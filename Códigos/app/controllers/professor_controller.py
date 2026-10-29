import os
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app.controllers.admin_controller import format_created_at
from app.controllers.document_controller import get_upload_folder
from app.database import get_session
from app.concurrency import check_version, begin_submission, finish_submission
from app.models import (
    AlunoModel,
    AlunoTurmaModel,
    AtividadeModel,
    DisciplinaModel,
    DocumentoModel,
    NotaModel,
    ProfessorDisciplinaModel,
    ProfessorModel,
    ProfessorTurmaModel,
    SolicitacaoDocumentoModel,
    TurmaDisciplinaModel,
    TurmaModel,
    UsuarioModel,
)


def get_professor_by_user_id(user_id):
    db = get_session()
    try:
        row = (
            db.query(ProfessorModel, UsuarioModel.email)
            .join(UsuarioModel, UsuarioModel.id == ProfessorModel.usuario_id)
            .filter(ProfessorModel.usuario_id == user_id)
            .first()
        )
        if not row:
            return None

        professor, email = row
        return {
            "id": professor.id,
            "nome": professor.nome,
            "email": email,
            "disciplina": professor.disciplina_principal or "Nao informado",
            "regime": professor.regime_trabalho or "Nao informado",
            "foto_perfil": professor.foto_perfil,
        }
    finally:
        db.close()


def _format_nota(value):
    if value is None:
        return ""

    return str(value).replace(".", ",")


def get_teacher_area_data(user_id):
    db = get_session()
    try:
        row = (
            db.query(ProfessorModel, UsuarioModel.email)
            .join(UsuarioModel, UsuarioModel.id == ProfessorModel.usuario_id)
            .filter(ProfessorModel.usuario_id == user_id)
            .first()
        )
        if not row:
            return None

        professor, email = row
        turma_rows = (
            db.query(TurmaModel)
            .join(ProfessorTurmaModel, ProfessorTurmaModel.turma_id == TurmaModel.id)
            .filter(ProfessorTurmaModel.professor_id == professor.id)
            .order_by(TurmaModel.nome.asc())
            .all()
        )
        turma_ids = [turma.id for turma in turma_rows]

        disciplinas_por_turma = {turma.id: [] for turma in turma_rows}
        alunos_por_turma = {turma.id: [] for turma in turma_rows}
        atividades_por_turma = {turma.id: [] for turma in turma_rows}

        if turma_ids:
            disciplina_rows = (
                db.query(TurmaDisciplinaModel.turma_id, DisciplinaModel)
                .join(DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id)
                .join(
                    ProfessorDisciplinaModel,
                    ProfessorDisciplinaModel.disciplina_id == DisciplinaModel.id,
                )
                .filter(TurmaDisciplinaModel.turma_id.in_(turma_ids))
                .filter(ProfessorDisciplinaModel.professor_id == professor.id)
                .order_by(DisciplinaModel.nome.asc())
                .distinct()
                .all()
            )
            for turma_id, disciplina in disciplina_rows:
                disciplinas_por_turma.setdefault(turma_id, []).append(
                    {
                        "id": disciplina.id,
                        "nome": disciplina.nome,
                        "codigo": disciplina.codigo,
                        "carga_horaria": disciplina.carga_horaria,
                    }
                )

            aluno_rows = (
                db.query(AlunoTurmaModel.turma_id, AlunoModel)
                .join(AlunoModel, AlunoModel.id == AlunoTurmaModel.aluno_id)
                .filter(AlunoTurmaModel.turma_id.in_(turma_ids))
                .order_by(AlunoModel.nome.asc())
                .all()
            )
            for turma_id, aluno in aluno_rows:
                alunos_por_turma.setdefault(turma_id, []).append(
                    {
                        "id": aluno.id,
                        "nome": aluno.nome,
                        "matricula": aluno.matricula,
                        "curso": aluno.curso_serie or "Nao informado",
                    }
                )

            atividade_rows = (
                db.query(AtividadeModel, DisciplinaModel)
                .join(DisciplinaModel, DisciplinaModel.id == AtividadeModel.disciplina_id)
                .filter(AtividadeModel.professor_id == professor.id)
                .filter(AtividadeModel.turma_id.in_(turma_ids))
                .order_by(AtividadeModel.id.desc())
                .limit(60)
                .all()
            )
            for atividade, disciplina in atividade_rows:
                atividades_por_turma.setdefault(atividade.turma_id, []).append(
                    {
                        "titulo": atividade.titulo,
                        "descricao": atividade.descricao or "Sem descricao.",
                        "disciplina": disciplina.nome,
                        "data_entrega": atividade.data_entrega or "Sem prazo",
                        "arquivo": atividade.caminho_arquivo,
                        "data": format_created_at(atividade.created_at),
                    }
                )

        notas_rows = (
            db.query(NotaModel, AlunoModel, DisciplinaModel, TurmaModel)
            .join(AlunoModel, AlunoModel.id == NotaModel.aluno_id)
            .join(DisciplinaModel, DisciplinaModel.id == NotaModel.disciplina_id)
            .join(AlunoTurmaModel, AlunoTurmaModel.aluno_id == AlunoModel.id)
            .join(TurmaModel, TurmaModel.id == AlunoTurmaModel.turma_id)
            .join(ProfessorTurmaModel, ProfessorTurmaModel.turma_id == TurmaModel.id)
            .filter(NotaModel.professor_id == professor.id)
            .filter(ProfessorTurmaModel.professor_id == professor.id)
            .order_by(NotaModel.id.desc())
            .limit(30)
            .all()
        )
        documentos_rows = (
            db.query(DocumentoModel, DisciplinaModel)
            .join(DisciplinaModel, DisciplinaModel.id == DocumentoModel.disciplina_id)
            .filter(
                DocumentoModel.professor_id == professor.id,
                DocumentoModel.aluno_id.is_(None),
            )
            .order_by(DocumentoModel.id.desc())
            .limit(30)
            .all()
        )
        solicitacoes_rows = (
            db.query(SolicitacaoDocumentoModel)
            .filter(SolicitacaoDocumentoModel.professor_id == professor.id)
            .order_by(SolicitacaoDocumentoModel.id.desc())
            .limit(30)
            .all()
        )

        grade_versions = {
            f"{n.aluno_id}:{n.disciplina_id}": n.versao
            for n in db.query(NotaModel).filter(
                NotaModel.aluno_id.in_([a["id"] for values in alunos_por_turma.values() for a in values])
            ).all()
        }
        return {
            "grade_versions": grade_versions,
            "professor": {
                "id": professor.id,
                "nome": professor.nome,
                "email": email,
                "disciplina": professor.disciplina_principal or "Nao informado",
                "regime": professor.regime_trabalho or "Nao informado",
                "foto_perfil": professor.foto_perfil,
            },
            "turmas": [
                {
                    "id": turma.id,
                    "nome": turma.nome,
                    "codigo": turma.codigo,
                    "ano_letivo": turma.ano_letivo,
                    "turno": turma.turno or "Nao informado",
                    "disciplinas": disciplinas_por_turma.get(turma.id, []),
                    "alunos": alunos_por_turma.get(turma.id, []),
                    "atividades": atividades_por_turma.get(turma.id, []),
                }
                for turma in turma_rows
            ],
            "notas": [
                {
                    "aluno": aluno.nome,
                    "matricula": aluno.matricula,
                    "disciplina": disciplina.nome,
                    "turma": turma.nome,
                    "nota": _format_nota(nota.nota),
                    "observacao": nota.observacao or "-",
                    "data": format_created_at(nota.data_lancamento),
                }
                for nota, aluno, disciplina, turma in notas_rows
            ],
            "documentos": [
                {
                    "titulo": documento.titulo,
                    "arquivo": documento.caminho_arquivo,
                    "disciplina": disciplina.nome,
                    "data": format_created_at(documento.data_envio),
                }
                for documento, disciplina in documentos_rows
            ],
            "solicitacoes_documentos": [
                {
                    "id": solicitacao.id,
                    "titulo": solicitacao.titulo,
                    "mensagem": solicitacao.mensagem or "Envie o documento solicitado pela secretaria.",
                    "status": solicitacao.status,
                    "status_label": "Enviado" if solicitacao.status == "enviado" else "Pendente",
                    "data": format_created_at(solicitacao.created_at),
                }
                for solicitacao in solicitacoes_rows
            ],
        }
    finally:
        db.close()


def launch_activity(user_id, data, files=None):
    from app.services.aprovacoes_service import submit_proposal
    from app.services.identidade_service import current_identity
    from app.concurrency import MutationConflict
    if current_identity().id != user_id:
        raise MutationConflict("Identidade divergente", 403)
    return submit_proposal("lancar_atividade", data, files)


def upload_requested_document(user_id, form, files):
    from app.services.aprovacoes_service import submit_proposal
    from app.services.identidade_service import current_identity
    from app.concurrency import MutationConflict
    if current_identity().id != user_id:
        raise MutationConflict("Identidade divergente", 403)
    return submit_proposal("responder_documento", form, files)


def save_student_grade(user_id, data):
    from app.services.aprovacoes_service import submit_proposal
    from app.services.identidade_service import current_identity
    from app.concurrency import MutationConflict
    if current_identity().id != user_id:
        raise MutationConflict("Identidade divergente", 403)
    return submit_proposal("salvar_nota", data)
