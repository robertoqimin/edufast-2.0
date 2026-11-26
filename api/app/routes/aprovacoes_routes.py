import json
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from app.concurrency import MutationConflict
from app.database import get_session
from app.models import AlunoModel, AlunoTurmaModel, ProfessorModel, ProfessorTurmaModel, SolicitacaoAlteracaoModel, UsuarioModel
from app.services.aprovacoes_service import can_review, decide_proposal, submit_proposal
from app.services.identidade_service import current_identity
from config import caminho_uploads

aprovacoes_bp = Blueprint("aprovacoes", __name__)


def _data():
    data = request.get_json(silent=True) if request.is_json else request.form
    if not isinstance(data, dict):
        raise MutationConflict("Corpo deve ser objeto", 400)
    return data


ESTADOS = {'pendentes': 'Pendentes', 'decididas': 'Decididas', 'todas': 'Todas'}


def _nomes(db, ids):
    """U5: nome legível (e perfil) de quem enviou ou decidiu, no lugar do número da conta."""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    perfis = {'admin': 'secretaria', 'super_admin': 'direção', 'professor': 'professor', 'aluno': 'aluno'}
    nomes = {u.id: (u.email, perfis.get(u.tipo, u.tipo)) for u in db.query(UsuarioModel).filter(UsuarioModel.id.in_(ids))}
    for model in (ProfessorModel, AlunoModel):
        for perfil in db.query(model).filter(model.usuario_id.in_(ids)):
            if perfil.usuario_id in nomes:
                nomes[perfil.usuario_id] = (perfil.nome, nomes[perfil.usuario_id][1])
    return {i: f'{nome} ({papel})' for i, (nome, papel) in nomes.items()}


def _items(identity, estado='todas'):
    with get_session() as db:
        query = db.query(SolicitacaoAlteracaoModel)
        if estado == 'pendentes':
            query = query.filter(SolicitacaoAlteracaoModel.estado == 'pendente')
        elif estado == 'decididas':
            query = query.filter(SolicitacaoAlteracaoModel.estado != 'pendente')
        if not identity.admin:
            if identity.revisor_materiais:
                query = query.filter((SolicitacaoAlteracaoModel.solicitante_id == identity.id) | (SolicitacaoAlteracaoModel.tipo == "lancar_atividade"))
            else:
                query = query.filter_by(solicitante_id=identity.id)
        rows = query.order_by(SolicitacaoAlteracaoModel.id.desc()).limit(100).all()
        nomes = _nomes(db, [r.solicitante_id for r in rows] + [r.decidido_por for r in rows])
        items = []
        for row in rows:
            own = row.solicitante_id == identity.id
            reviewer = can_review(db, identity, row) if not own else False
            if not own and not reviewer:
                continue
            items.append({"id": row.id, "tipo": row.tipo, "estado": row.estado,
                "solicitante_id": row.solicitante_id, "payload": json.loads(row.payload),
                "decidido_por": row.decidido_por, "justificativa": row.justificativa,
                "pode_decidir": reviewer and row.estado == "pendente", "tem_arquivo": bool(row.arquivo),
                "solicitante": nomes.get(row.solicitante_id, f"Conta {row.solicitante_id}"),
                "decisor": nomes.get(row.decidido_por) if row.decidido_por else None,
                "decidida_em": row.decided_at.strftime('%d/%m/%Y às %H:%M') if hasattr(row.decided_at, 'strftime') else None})
            from app.presenters.aprovacoes_presenter import present
            items[-1]['titulo'], items[-1]['campos'] = present(row.tipo, json.loads(row.payload))
            if row.tipo == 'publicar_material':
                items[-1]['conteudo_url'] = url_for('estudos.conteudo',content_id=json.loads(row.payload)['conteudo_id'])
            data = json.loads(row.payload)
            if row.tipo == 'operacao_restaurada' and data.get('endpoint') == 'academico.lancar_lote':
                from app.services.academico import resumo_lote
                avaliacao_id = data.get('params', {}).get('avaliacao_id')
                resumo = resumo_lote(db, avaliacao_id, data.get('payload', {}))
                if resumo:
                    items[-1]['titulo'] = 'Lançar notas da avaliação'
                    items[-1]['campos'] = {'Avaliação': resumo['avaliacao'], 'Turma': resumo['turma'],
                                           'Disciplina': resumo['disciplina']}
                    items[-1]['diario_url'] = url_for('academico.diario', avaliacao_id=avaliacao_id)
                    if row.estado == 'pendente':
                        # A comparação "atual → enviada" só faz sentido antes da decisão.
                        items[-1]['campos']['Notas no envio'] = f"{len(resumo['linhas'])} ({resumo['novas']} novas, {resumo['alteradas']} alteradas)"
                        items[-1]['notas'] = resumo['linhas']
                    else:
                        items[-1]['campos']['Notas no envio'] = len(resumo['linhas'])
            if row.tipo == 'publicar_curso':
                from app.models import CursoModel
                data = json.loads(row.payload)
                course = db.get(CursoModel,data['curso_id'])
                items[-1]['titulo'] = 'Publicar curso de aprendizagem'
                items[-1]['campos'] = {'Curso':course.titulo if course else 'Curso indisponível','Edição enviada':data['versao']}
                items[-1]['curso_url'] = url_for('cursos_web.editor',curso_id=data['curso_id'])
            if identity.admin and row.tipo == "cadastro":
                user = db.get(UsuarioModel, row.solicitante_id)
                profile = (db.query(ProfessorModel).filter_by(usuario_id=row.solicitante_id).first()
                           or db.query(AlunoModel).filter_by(usuario_id=row.solicitante_id).first())
                items[-1]["candidato"] = {"email": user.email if user else "", "nome": profile.nome if profile else "", "cpf": profile.cpf if profile else None}
        return items


@aprovacoes_bp.get("/solicitacoes")
def painel():
    identity = current_identity()
    if identity.papel not in {"admin", "super_admin", "professor"}:
        raise MutationConflict("Acesso não autorizado", 403)
    alunos = []
    docentes = []
    if identity.admin:
        with get_session() as db:
            rows = (db.query(ProfessorModel, UsuarioModel).join(UsuarioModel, UsuarioModel.id == ProfessorModel.usuario_id)
                    .filter(UsuarioModel.tipo == 'professor', UsuarioModel.estado == 'ativo').order_by(ProfessorModel.nome).all())
            docentes = [{'usuario_id': user.id, 'nome': profile.nome, 'email': user.email,
                         'revisor': user.revisor_materiais} for profile, user in rows]
    if identity.papel == "professor":
        with get_session() as db:
            rows = (db.query(AlunoModel).join(AlunoTurmaModel, AlunoTurmaModel.aluno_id == AlunoModel.id)
                    .join(ProfessorTurmaModel, ProfessorTurmaModel.turma_id == AlunoTurmaModel.turma_id)
                    .join(ProfessorModel, ProfessorModel.id == ProfessorTurmaModel.professor_id)
                    .filter(ProfessorModel.usuario_id == identity.id).distinct().order_by(AlunoModel.nome).all())
            alunos = [{"id": r.id, "nome": r.nome, "matricula": r.matricula, "curso": r.curso_serie or "", "versao": r.versao} for r in rows]
    estado = request.args.get("estado", "pendentes")
    if estado not in ESTADOS:
        estado = "pendentes"
    visiveis = _items(identity)  # contagens do filtro, com a mesma visibilidade da lista
    contagem = {'pendentes': sum(i['estado'] == 'pendente' for i in visiveis),
                'decididas': sum(i['estado'] != 'pendente' for i in visiveis), 'todas': len(visiveis)}
    return render_template("solicitacoes.html", identity=identity, solicitacoes=_items(identity, estado), alunos=alunos,
                           docentes=docentes, estado=estado, estados=ESTADOS, contagem=contagem)


@aprovacoes_bp.route("/solicitacoes/alteracoes", methods=["GET", "POST"])
def alteracoes():
    identity = current_identity()
    if identity.papel not in {"admin", "super_admin", "professor"}:
        raise MutationConflict("Acesso não autorizado", 403)
    if request.method == "GET":
        return jsonify({"solicitacoes": _items(identity)})
    data = dict(_data() or {})
    kind = data.pop("tipo", None)
    payload = data.pop("payload", data)
    if not isinstance(payload, dict):
        raise MutationConflict("Payload deve ser objeto", 400)
    body, status = submit_proposal(kind, payload, request.files)
    if request.is_json or request.accept_mimetypes.best == "application/json":
        return jsonify(body), status
    return redirect(url_for("aprovacoes.painel"))


@aprovacoes_bp.post("/solicitacoes/alteracoes/<int:proposal_id>/decidir")
def decidir(proposal_id):
    data = _data() or {}
    body, status = decide_proposal(proposal_id, data.get("decisao"), data.get("justificativa", ""))
    if request.is_json or request.accept_mimetypes.best == "application/json":
        return jsonify(body), status
    return redirect(url_for("aprovacoes.painel"))


@aprovacoes_bp.post("/solicitacoes/alteracoes/lote")
def decidir_lote():
    """U3/O1: aprovar ou rejeitar várias solicitações de uma vez.

    Cada uma é decidida na sua própria transação, com as mesmas regras da decisão individual
    (permissão, versão, conteúdo inalterado desde o envio); uma falha não desfaz as outras.
    """
    data = _data() or {}
    ids = data.get("ids", []) if request.is_json else request.form.getlist("ids")
    if not isinstance(ids, list) or not ids or len(ids) > 100:
        raise MutationConflict("Selecione de 1 a 100 solicitações.", 400)
    try:
        ids = sorted({int(i) for i in ids})
    except (TypeError, ValueError):
        raise MutationConflict("Solicitação inválida.", 400)
    decisao, justificativa = data.get("decisao"), data.get("justificativa", "")
    if decisao not in {"aprovar", "rejeitar"}:
        raise MutationConflict("Decisão inválida.", 400)
    decididas, falhas = [], []
    for proposal_id in ids:
        try:
            decide_proposal(proposal_id, decisao, justificativa)
            decididas.append(proposal_id)
        except MutationConflict as error:
            falhas.append({"id": proposal_id, "erro": error.message})
    if request.is_json or request.accept_mimetypes.best == "application/json":
        return jsonify(decididas=decididas, falhas=falhas), 200
    verbo = "aprovadas" if decisao == "aprovar" else "rejeitadas"
    if decididas:
        flash(f"{len(decididas)} solicitações {verbo}.", "success")
    for falha in falhas:
        flash(f"Solicitação {falha['id']} não foi decidida: {falha['erro']}", "error")
    return redirect(url_for("aprovacoes.painel"))


@aprovacoes_bp.get("/solicitacoes/alteracoes/<int:proposal_id>/arquivo")
def arquivo(proposal_id):
    from flask import current_app, send_from_directory
    identity = current_identity()
    with get_session() as db:
        row = db.get(SolicitacaoAlteracaoModel, proposal_id)
        if row is None or not row.arquivo:
            raise MutationConflict("Arquivo não encontrado", 404)
        if row.solicitante_id != identity.id and not can_review(db, identity, row):
            raise MutationConflict("Arquivo não encontrado", 404)
        return send_from_directory(caminho_uploads(current_app.config["UPLOAD_FOLDER"]), row.arquivo, as_attachment=True)


@aprovacoes_bp.post("/admin/usuarios/<int:user_id>/permissoes")
def permissoes(user_id):
    identity = current_identity()
    if not identity.admin:
        raise MutationConflict("Acesso não autorizado", 403)
    data = _data() or {}
    if set(data) - {"papel", "revisor_materiais"}:
        raise MutationConflict("Campos não permitidos", 400)
    with get_session() as db:
        user = db.query(UsuarioModel).filter_by(id=user_id).with_for_update().first()
        if not user or user.estado != "ativo":
            raise MutationConflict("Usuário ativo não encontrado", 404)
        role = data.get("papel", user.tipo)
        if not isinstance(role, str):
            raise MutationConflict("Papel inválido", 400)
        role = role.lower()
        if user.tipo == 'super_admin' and role != user.tipo:
            raise MutationConflict('O superperfil protegido não pode ser rebaixado', 403)
        if "papel" in data and (identity.papel != "super_admin" or identity.id == user.id):
            raise MutationConflict("Somente superadmin pode atribuir papeis a outras contas", 403)
        if role not in {"admin", "super_admin", "professor", "aluno"}:
            raise MutationConflict("Papel inválido", 400)
        flag = data.get("revisor_materiais", user.revisor_materiais)
        if flag not in (True, False, "true", "false", "1", "0"):
            raise MutationConflict("Permissão inválida", 400)
        reviewer = flag in (True, "true", "1")
        if (role == "professor" or reviewer) and db.query(ProfessorModel.id).filter_by(usuario_id=user_id).first() is None:
            raise MutationConflict("Conta sem cadastro docente", 400)
        if reviewer and role != "professor":
            raise MutationConflict("Revisor deve ser professor", 400)
        if role == "aluno" and db.query(AlunoModel.id).filter_by(usuario_id=user_id).first() is None:
            raise MutationConflict("Conta sem cadastro de aluno", 400)
        user.tipo, user.revisor_materiais = role, reviewer
        user.auth_version += 1
        db.commit()
    return jsonify({"id": user_id, "papel": role, "revisor_materiais": reviewer})
