from datetime import date

from flask import abort
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.services.arquivos_service import _remove_saved_file, _save_profile_photo
from app.database import get_session
from app.concurrency import check_version, insert_if_missing, begin_submission, finish_submission
from app.models import (
    AlunoModel,
    AlunoTurmaModel,
    ComunicadoModel,
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


def request_student_document(aluno_id, data, *, session_factory=get_session):
    titulo = (data.get("titulo") or "").strip()
    mensagem = (data.get("mensagem") or "").strip()

    if not titulo:
        return {"erro": "Titulo do documento e obrigatorio"}, 400

    db = session_factory()
    try:
        entry, replay = begin_submission(db, f"solicitar-aluno:{aluno_id}")
        if replay:
            return replay
        aluno = db.get(AlunoModel, aluno_id)
        if not aluno:
            return {"erro": "Aluno nao encontrado"}, 404

        solicitacao = SolicitacaoDocumentoModel(
            aluno_id=aluno.id,
            titulo=titulo[:150],
            mensagem=mensagem or None,
            status="pendente",
        )
        db.add(solicitacao)
        db.flush()
        return finish_submission(db, entry, {"id": solicitacao.id}, 201)
    finally:
        db.close()

def request_professor_document(professor_id, data, *, session_factory=get_session):
    titulo = (data.get("titulo") or "").strip()
    mensagem = (data.get("mensagem") or "").strip()

    if not titulo:
        return {"erro": "Titulo do documento e obrigatorio"}, 400

    db = session_factory()
    try:
        entry, replay = begin_submission(db, f"solicitar-professor:{professor_id}")
        if replay:
            return replay
        professor = db.get(ProfessorModel, professor_id)
        if not professor:
            return {"erro": "Professor nao encontrado"}, 404

        solicitacao = SolicitacaoDocumentoModel(
            professor_id=professor.id,
            titulo=titulo[:150],
            mensagem=mensagem or None,
            status="pendente",
        )
        db.add(solicitacao)
        db.flush()
        return finish_submission(db, entry, {"id": solicitacao.id}, 201)
    finally:
        db.close()
