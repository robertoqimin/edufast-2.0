import os
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename

from app.database import get_session
from app.concurrency import insert_if_missing
from app.models import AlunoModel, DisciplinaModel, DocumentoModel, ProfessorModel
from app.models import SolicitacaoDocumentoModel
from datetime import datetime
from sqlalchemy import update
from app.concurrency import begin_submission, finish_submission


def get_upload_folder():
    return os.path.abspath(current_app.config["UPLOAD_FOLDER"])


def _get_or_create_disciplina(session_db, disciplina_id=None):
    if disciplina_id:
        disciplina = session_db.get(DisciplinaModel, disciplina_id)
        if disciplina:
            return disciplina, None

        return None, ({"erro": "Disciplina nao encontrada"}, 404)

    disciplina = insert_if_missing(session_db, DisciplinaModel,
                                   codigo="GERAL", defaults={"nome": "Geral", "carga_horaria": 0})
    return disciplina, None


def upload_documento(form, files, current_user=None, is_admin=False, aluno_id_override=None):
    if "arquivo" not in files:
        return {"erro": "Arquivo nao enviado"}, 400

    aluno_id = aluno_id_override or form.get("aluno_id", type=int)
    if not aluno_id:
        return {"erro": "aluno_id e obrigatorio"}, 400

    arquivo = files["arquivo"]
    if not arquivo.filename:
        return {"erro": "Nome do arquivo nao informado"}, 400

    session_db = get_session()
    upload_folder = get_upload_folder()
    os.makedirs(upload_folder, exist_ok=True)
    saved_path = None

    try:
        entry, replay = begin_submission(
            session_db, f"documento-aluno:{aluno_id}",
            actor=current_user["sub"] if current_user and not is_admin else None)
        if replay:
            return replay
        aluno = session_db.get(AlunoModel, aluno_id)
        if not aluno:
            return {"erro": "Aluno nao encontrado"}, 404

        professor = None
        if not is_admin and current_user:
            professor = (
                session_db.query(ProfessorModel)
                .filter(ProfessorModel.usuario_id == int(current_user["sub"]))
                .first()
            )
            if not professor:
                return {"erro": "Professor nao encontrado para o usuario autenticado"}, 403

        disciplina, error = _get_or_create_disciplina(
            session_db,
            form.get("disciplina_id", type=int),
        )
        if error:
            return error

        original_filename = secure_filename(arquivo.filename)
        if not original_filename:
            return {"erro": "Nome do arquivo invalido"}, 400

        filename = f"{uuid4().hex}_{original_filename}"
        saved_path = os.path.join(upload_folder, filename)
        arquivo.save(saved_path)

        documento = DocumentoModel(
            aluno_id=aluno.id,
            professor_id=professor.id if professor else None,
            disciplina_id=disciplina.id,
            titulo=(form.get("titulo") or original_filename)[:150],
            caminho_arquivo=filename,
        )
        session_db.add(documento)
        session_db.flush()
        body = {
            "mensagem": "Arquivo enviado",
            "documento": {
                "id": documento.id,
                "titulo": documento.titulo,
                "arquivo": documento.caminho_arquivo,
                "aluno_id": documento.aluno_id,
                "professor_id": documento.professor_id,
                "disciplina_id": documento.disciplina_id,
            },
        }
        return finish_submission(session_db, entry, body, 201)
    except Exception:
        session_db.rollback()
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)
        raise
    finally:
        session_db.close()


def upload_requested_document_for_owner(owner_column, owner_id, request_id, files):
    """Claim pending request and create its document in one transaction."""
    if owner_column not in {"aluno_id", "professor_id"}:
        raise ValueError("Invalid document owner")
    arquivo = files.get("arquivo")
    original = secure_filename(arquivo.filename or "") if arquivo else ""
    if not request_id or not original:
        return {"erro": "Solicitacao e arquivo sao obrigatorios"}, 400
    db = get_session()
    saved_path = None
    committed = False
    try:
        owner = getattr(SolicitacaoDocumentoModel, owner_column)
        criteria = (SolicitacaoDocumentoModel.id == request_id, owner == owner_id)
        result = db.execute(update(SolicitacaoDocumentoModel).where(
            *criteria, SolicitacaoDocumentoModel.status == "pendente"
        ).values(status="enviado", completed_at=datetime.now()))
        if result.rowcount != 1:
            exists = db.query(SolicitacaoDocumentoModel.id).filter(*criteria).first()
            return {"erro": "Solicitacao ja respondida" if exists else "Solicitacao nao encontrada"}, 409 if exists else 404
        solicitacao = db.get(SolicitacaoDocumentoModel, request_id)
        disciplina, _ = _get_or_create_disciplina(db)
        folder = get_upload_folder()
        os.makedirs(folder, exist_ok=True)
        filename = f"{uuid4().hex}_{original}"
        saved_path = os.path.join(folder, filename)
        arquivo.save(saved_path)
        documento = DocumentoModel(**{owner_column: owner_id}, disciplina_id=disciplina.id,
                                   titulo=solicitacao.titulo, caminho_arquivo=filename)
        db.add(documento)
        db.flush()
        solicitacao.documento_id = documento.id
        db.commit()
        committed = True
        return {"mensagem": "Documento enviado"}, 201
    finally:
        db.close()
        if saved_path and not committed:
            try:
                os.remove(saved_path)
            except FileNotFoundError:
                pass
