"""Allowlisted proposals. Approval and its domain effect share one DB transaction."""
import json
import os
from datetime import date, datetime
from uuid import uuid4

from flask import current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app.concurrency import MutationConflict, begin_submission, check_version, finish_submission
from app.database import get_session
from app.models import (AlunoModel, AlunoTurmaModel, AtividadeModel, DisciplinaModel,
                        DocumentoModel, ProfessorDisciplinaModel, ProfessorModel,
                        ProfessorTurmaModel, SolicitacaoAlteracaoModel, SolicitacaoDocumentoModel,
                        TurmaDisciplinaModel, TurmaModel, UsuarioModel)
from app.services.identidade_service import current_identity
from config import caminho_uploads

FIELDS = {
    "publicar_curso": {"curso_id", "versao"},
    "publicar_material": {"conteudo_id", "versao"},
    "operacao_restaurada": {"endpoint", "params", "payload"},
    "criar_turma": {"nome", "codigo", "ano_letivo", "turno"},
    "criar_disciplina": {"nome", "codigo", "carga_horaria"},
    "editar_aluno": {"aluno_id", "nome", "curso_serie", "versao"},
    "lancar_atividade": {"turma_id", "disciplina_id", "titulo", "descricao", "data_entrega"},
    "enviar_documento": {"aluno_id", "disciplina_id", "titulo"},
    "responder_documento": {"solicitacao_id"},
}
# B1: notas são lançadas só no diário da avaliação (academico_notas). Propostas antigas
# pendentes continuam listadas e podem ser rejeitadas, mas nunca gravam em `notas`.
LEGADOS = {"salvar_nota": "Notas agora sao lancadas no diario da avaliacao (/academico)."}


# U1/O4: nomes de campo legíveis nas mensagens (nunca o nome interno do formulário).
ROTULOS = {'titulo': 'título', 'nome': 'nome', 'codigo': 'código', 'descricao': 'descrição', 'data_entrega': 'data de entrega',
           'turma_id': 'turma', 'disciplina_id': 'disciplina', 'aluno_id': 'aluno', 'ano_letivo': 'ano letivo',
           'carga_horaria': 'carga horária', 'curso_serie': 'curso/série', 'versao': 'versão', 'turno': 'turno',
           'solicitacao_id': 'solicitação', 'observacao': 'observação'}


def _text(data, name, maximum, required=False):
    value = str(data.get(name) or "").strip()
    if (required and not value) or len(value) > maximum:
        raise MutationConflict(f"Confira o campo {ROTULOS.get(name, name)}.", 400)
    return value


def _integer(data, name, minimum=1):
    try:
        raw = data.get(name)
        if isinstance(raw, bool):
            raise ValueError()
        result = int(str(raw))
        if result < minimum:
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise MutationConflict(f"Confira o campo {ROTULOS.get(name, name)}.", 400)


def _teacher(db, user_id):
    user = db.get(UsuarioModel, user_id)
    professor = db.query(ProfessorModel).filter_by(usuario_id=user_id).first()
    if not user or user.estado != "ativo" or user.tipo.lower() != "professor" or not professor:
        raise MutationConflict("Professor sem acesso ativo", 403)
    return professor


def _scope(db, professor, turma_id, disciplina_id, aluno_id=None):
    pairs = [(ProfessorTurmaModel, {"professor_id": professor.id, "turma_id": turma_id}),
             (ProfessorDisciplinaModel, {"professor_id": professor.id, "disciplina_id": disciplina_id}),
             (TurmaDisciplinaModel, {"turma_id": turma_id, "disciplina_id": disciplina_id})]
    if aluno_id is not None:
        pairs.append((AlunoTurmaModel, {"aluno_id": aluno_id, "turma_id": turma_id}))
    if any(db.query(model.id).filter_by(**keys).first() is None for model, keys in pairs):
        raise MutationConflict("Recurso fora dos vínculos autorizados", 403)


def _student(db, professor, aluno_id):
    row = (db.query(AlunoModel).join(AlunoTurmaModel, AlunoTurmaModel.aluno_id == AlunoModel.id)
           .join(ProfessorTurmaModel, ProfessorTurmaModel.turma_id == AlunoTurmaModel.turma_id)
           .filter(AlunoModel.id == aluno_id, ProfessorTurmaModel.professor_id == professor.id).first())
    if row is None:
        raise MutationConflict("Aluno não encontrado no escopo autorizado", 404)
    return row


def validate_proposal(db, user_id, kind, raw):
    if not isinstance(kind, str) or kind not in FIELDS or not isinstance(raw, dict) or set(raw) - FIELDS[kind]:
        raise MutationConflict("Operação ou campos não permitidos", 400)
    professor = _teacher(db, user_id)
    data = dict(raw)
    if kind == 'publicar_curso':
        from app.services.cursos_ms04.publicacao import preparar_publicacao
        return preparar_publicacao(db,autor_id=user_id,curso_id=data.get('curso_id'),versao=data.get('versao'))
    if kind == 'publicar_material':
        from app.services.estudo_service import prepare_publication
        return prepare_publication(db,user_id,data)
    if kind == 'operacao_restaurada':
        from app.services.restauracao_context import execute
        execute(db, user_id, data, validate=True)
        return data
    for key in ("aluno_id", "turma_id", "disciplina_id", "solicitacao_id"):
        if key in FIELDS[kind]:
            data[key] = _integer(data, key)
    if kind == "lancar_atividade":
        _scope(db, professor, data["turma_id"], data["disciplina_id"], data.get("aluno_id"))
    if kind == "editar_aluno":
        row = _student(db, professor, data["aluno_id"])
        data["versao"] = _integer(data, "versao", 0)
        if data["versao"] != row.versao:
            raise MutationConflict("Registro alterado; recarregue antes de solicitar")
        data["nome"] = _text(data, "nome", 120, True)
        data["curso_serie"] = _text(data, "curso_serie", 80)
    if kind in {"criar_turma", "criar_disciplina"}:
        data["nome"] = _text(data, "nome", 120, True)
        data["codigo"] = _text(data, "codigo", 30, True).upper()
        if kind == "criar_turma":
            data["ano_letivo"] = _integer(data, "ano_letivo", 2000)
            data["turno"] = _text(data, "turno", 30)
        else:
            data["carga_horaria"] = _integer(data, "carga_horaria", 0)
    if kind == "lancar_atividade":
        data["titulo"] = _text(data, "titulo", 150, True)
        data["descricao"] = _text(data, "descricao", 10000)
        value = _text(data, "data_entrega", 10)
        try:
            data["data_entrega"] = date.fromisoformat(value).isoformat() if value else None
        except ValueError:
            raise MutationConflict("Data de entrega inválida", 400)
    if kind == "enviar_documento":
        _student(db, professor, data["aluno_id"])
        turma = (db.query(AlunoTurmaModel.turma_id)
                 .join(ProfessorTurmaModel, ProfessorTurmaModel.turma_id == AlunoTurmaModel.turma_id)
                 .join(TurmaDisciplinaModel, TurmaDisciplinaModel.turma_id == AlunoTurmaModel.turma_id)
                 .filter(AlunoTurmaModel.aluno_id == data["aluno_id"], ProfessorTurmaModel.professor_id == professor.id,
                         TurmaDisciplinaModel.disciplina_id == data["disciplina_id"]).first())
        if turma is None:
            raise MutationConflict("Disciplina fora do escopo autorizado", 403)
        _scope(db, professor, turma[0], data["disciplina_id"], data["aluno_id"])
        data["titulo"] = _text(data, "titulo", 150) or "Documento solicitado"
    if kind == "responder_documento":
        row = db.query(SolicitacaoDocumentoModel).filter_by(id=data["solicitacao_id"], professor_id=professor.id).first()
        if row is None:
            raise MutationConflict("Solicitação não encontrada", 404)
        if row.status != "pendente":
            raise MutationConflict("Solicitação já respondida")
    return data


def submit_proposal(kind, data, files=None):
    identity = current_identity()
    if identity.papel != "professor":
        raise MutationConflict("Somente professores podem enviar propostas", 403)
    if isinstance(kind, str) and kind in LEGADOS:
        raise MutationConflict(LEGADOS[kind], 410)
    if not isinstance(kind, str) or kind not in FIELDS:
        raise MutationConflict("Operação ou campos não permitidos", 400)
    db = get_session()
    filename = None
    committed = False
    try:
        operation = 'proposta:' + kind
        if kind == 'publicar_curso':
            from app.services.cursos_ms04.comum import inteiro
            operation += ':' + str(inteiro(data.get('curso_id')))
        if kind == 'publicar_material':
            from app.services.frequencia_service import integer
            operation += ':' + str(integer(data.get('conteudo_id')))
        entry, replay = begin_submission(db, operation, actor=identity.id)
        if replay:
            return replay
        raw = {k: v for k, v in dict(data).items() if k not in {"idempotency_key", "redirect_to", "csrf_token"}}
        normalized = validate_proposal(db, identity.id, kind, raw)
        file = files.get("arquivo") if files else None
        if kind in {'publicar_material','publicar_curso'} and file:
            raise MutationConflict('Anexe o arquivo ao rascunho antes de pedir publicação.',400)
        if kind in {"enviar_documento", "responder_documento"} and (not file or not file.filename):
            raise MutationConflict("Arquivo obrigatório", 400)
        if file and file.filename:
            original = secure_filename(file.filename)
            if not original:
                raise MutationConflict("Nome de arquivo inválido", 400)
            filename = "pendente_" + uuid4().hex + "_" + original
            os.makedirs(caminho_uploads(current_app.config["UPLOAD_FOLDER"]), exist_ok=True)
            file.save(os.path.join(caminho_uploads(current_app.config["UPLOAD_FOLDER"]), filename))
        resource = None
        if kind == 'publicar_curso':
            resource = f"curso:{normalized['curso_id']}:{normalized['versao']}"
        if kind == 'publicar_material':
            resource = f"estudo:{normalized['conteudo_id']}:{normalized['versao']}"
        if kind == "responder_documento":
            resource = f"documento:{normalized['solicitacao_id']}"
        if kind == 'operacao_restaurada' and normalized.get('endpoint') == 'academico.lancar_lote':
            resource = f"notas:{normalized['params']['avaliacao_id']}"
        proposal = SolicitacaoAlteracaoModel(solicitante_id=identity.id, tipo=kind,
            payload=json.dumps(normalized, ensure_ascii=False), estado="pendente", arquivo=filename, recurso_pendente=resource)
        db.add(proposal)
        db.flush()
        result = finish_submission(db, entry, {"id": proposal.id, "estado": "pendente", "mensagem": "Solicitação enviada para aprovação"}, 202)
        committed = True
        return result
    except IntegrityError:
        db.rollback()
        raise MutationConflict("Já existe solicitação pendente para este recurso")
    finally:
        db.close()
        if filename and not committed:
            try:
                os.remove(os.path.join(caminho_uploads(current_app.config["UPLOAD_FOLDER"]), filename))
            except FileNotFoundError:
                pass


def can_review(db, identity, proposal):
    if identity.admin:
        return True
    if identity.revisor_materiais and identity.papel == 'professor' and proposal.tipo == 'operacao_restaurada':
        from app.services.restauracao_context import material_discipline
        discipline = material_discipline(db, json.loads(proposal.payload))
        professor = _teacher(db, identity.id)
        return discipline is not None and db.query(ProfessorDisciplinaModel.id).filter_by(professor_id=professor.id, disciplina_id=discipline).first() is not None
    if not identity.revisor_materiais or identity.papel != "professor" or proposal.tipo != "lancar_atividade":
        return False
    data = json.loads(proposal.payload)
    professor = _teacher(db, identity.id)
    return db.query(ProfessorDisciplinaModel.id).filter_by(
        professor_id=professor.id, disciplina_id=data["disciplina_id"]).first() is not None


def _apply(db, proposal):
    if proposal.tipo in LEGADOS:
        raise MutationConflict("Proposta de nota do painel antigo: rejeite e peça o lançamento no diário da avaliação")
    data = json.loads(proposal.payload)
    if proposal.tipo == 'publicar_curso':
        from app.services.cursos_ms04.publicacao import preparar_publicacao
        preparar_publicacao(db,autor_id=proposal.solicitante_id,curso_id=data['curso_id'],
            versao=data['versao'],assinatura=data['snapshot'],aplicar=True)
        return
    if proposal.tipo == 'publicar_material':
        from app.services.estudo_service import prepare_publication
        prepare_publication(db,proposal.solicitante_id,data,apply=True)
        return
    if proposal.tipo == 'operacao_restaurada':
        from app.services.restauracao_context import execute
        execute(db, proposal.solicitante_id, data, unidade=proposal.unidade_id)
        return
    if proposal.tipo == "cadastro":
        user = db.get(UsuarioModel, data["usuario_id"])
        role = data["papel_solicitado"]
        profile = ProfessorModel if role == "professor" else AlunoModel
        if (role not in {"professor", "aluno"} or user is None or user.id != proposal.solicitante_id
                or user.estado != "pendente" or db.query(profile.id).filter_by(usuario_id=user.id).first() is None):
            raise MutationConflict("Cadastro pendente inválido")
        user.tipo, user.estado, user.revisor_materiais = role, "ativo", False
        user.auth_version += 1
        if role == "aluno":
            db.query(AlunoModel).filter_by(usuario_id=user.id).one().status_matricula = "Ativo"
        return
    data = validate_proposal(db, proposal.solicitante_id, proposal.tipo, data)
    professor = _teacher(db, proposal.solicitante_id)
    # Unidades: o que o professor pediu nasce na unidade da solicitação, não na de quem aprova.
    if proposal.tipo == "criar_turma":
        db.add(TurmaModel(**{**data, "unidade_id": proposal.unidade_id}))
    elif proposal.tipo == "criar_disciplina":
        db.add(DisciplinaModel(**{**data, "unidade_id": proposal.unidade_id}))
    elif proposal.tipo == "editar_aluno":
        aluno = _student(db, professor, data["aluno_id"])
        check_version(aluno, data)
        aluno.nome, aluno.curso_serie = data["nome"], data["curso_serie"] or None
    elif proposal.tipo == "lancar_atividade":
        db.add(AtividadeModel(professor_id=professor.id, caminho_arquivo=proposal.arquivo, **data))
    elif proposal.tipo == "enviar_documento":
        db.add(DocumentoModel(professor_id=professor.id, caminho_arquivo=proposal.arquivo, **data))
    elif proposal.tipo == "responder_documento":
        from app.controllers.document_controller import _get_or_create_disciplina
        row = db.query(SolicitacaoDocumentoModel).filter_by(id=data["solicitacao_id"], professor_id=professor.id).with_for_update().one()
        if row.status != "pendente":
            raise MutationConflict("Solicitação já respondida")
        disciplina, _ = _get_or_create_disciplina(db)
        document = DocumentoModel(professor_id=professor.id, disciplina_id=disciplina.id,
                                  titulo=row.titulo, caminho_arquivo=proposal.arquivo)
        db.add(document)
        db.flush()
        row.documento_id, row.status, row.completed_at = document.id, "enviado", datetime.now()


def decide_proposal(proposal_id, decision, reason=""):
    identity = current_identity()
    if decision not in {"aprovar", "rejeitar"}:
        raise MutationConflict("Decisão inválida", 400)
    with get_session() as db:
        proposal = db.query(SolicitacaoAlteracaoModel).filter_by(id=proposal_id).with_for_update().first()
        if proposal is None:
            raise MutationConflict("Solicitação não encontrada", 404)
        if identity.id == proposal.solicitante_id or not can_review(db, identity, proposal):
            raise MutationConflict("Sem permissão para decidir esta solicitação", 403)
        if proposal.estado != "pendente":
            raise MutationConflict("Solicitação já decidida")
        if decision == "aprovar":
            _apply(db, proposal)
        proposal.estado = "aprovada" if decision == "aprovar" else "rejeitada"
        proposal.decidido_por, proposal.decided_at = identity.id, datetime.now()
        proposal.justificativa = str(reason).strip()[:500] or None
        proposal.recurso_pendente = None
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise MutationConflict("Alteração conflita com dados existentes")
        return {"id": proposal.id, "estado": proposal.estado}, 200
