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


def get_comunicados(limit=8, *, session_factory=get_session):
    from app.repositories.comunicados_repository import load_get_comunicados
    from app.presenters.admin_presenter import present_get_comunicados
    db = session_factory()
    try:
        values = load_get_comunicados(db, limit)
        return present_get_comunicados(**values)
    except LookupError:
        abort(404)
    finally:
        db.close()


def criar_comunicado(data, criado_por=None, *, session_factory=get_session):
    titulo = (data.get("titulo") or "").strip()
    destinatario = (data.get("destinatario") or "Geral").strip()
    mensagem = (data.get("mensagem") or "").strip()

    if not titulo or not mensagem:
        return {"erro": "Titulo e mensagem sao obrigatorios"}, 400

    db = session_factory()
    try:
        entry, replay = begin_submission(db, "comunicado")
        if replay:
            return replay
        comunicado = ComunicadoModel(
            titulo=titulo,
            destinatario=destinatario,
            mensagem=mensagem,
            criado_por=criado_por,
        )
        db.add(comunicado)
        db.flush()
        return finish_submission(db, entry, {"id": comunicado.id}, 201)
    finally:
        db.close()
