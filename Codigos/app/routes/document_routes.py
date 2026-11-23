import os
from uuid import uuid4

from flask import Blueprint, jsonify, redirect, request, send_from_directory, session
from werkzeug.utils import secure_filename

from app.auth import decode_token_from_request, normalize_role
from app.services.identidade_service import current_identity
from app.services.acesso_arquivos_service import allowed_file
from app.concurrency import MutationConflict
from app.controllers.document_controller import get_upload_folder, upload_documento
from app.database import get_session
from app.concurrency import insert_if_missing, begin_submission, finish_submission
from app.models import (
    AlunoModel,
    AlunoTurmaModel,
    AtividadeModel,
    DisciplinaModel,
    DocumentoModel,
    ProfessorModel,
)

document_bp = Blueprint("document", __name__)


def _get_or_create_disciplina_geral(db):
    disciplina = insert_if_missing(db, DisciplinaModel,
                                   codigo="GERAL", defaults={"nome": "Geral", "carga_horaria": 0})
    return disciplina


@document_bp.route('/arquivos/upload', methods=['POST'])
def upload_arquivo():
    identity = current_identity()
    is_admin = identity.admin
    jwt_payload = {"sub": str(identity.id), "role": identity.papel}
    if not is_admin and identity.papel != "professor":
        raise MutationConflict("Acesso nao autorizado", 403)

    if "arquivo" not in request.files:
        return jsonify({"erro": "Arquivo nao enviado"}), 400

    response, status = upload_documento(
        request.form,
        request.files,
        current_user=jwt_payload,
        is_admin=is_admin,
    )

    redirect_to = request.form.get("redirect_to")
    if 200 <= status < 300 and redirect_to and redirect_to.startswith("/") and not redirect_to.startswith("//") and "\\" not in redirect_to:
        return redirect(redirect_to)

    return jsonify(response), status


@document_bp.route('/arquivos/download/<path:filename>', methods=['GET'])
def download_arquivo(filename):
    return _serve_authorized_file(filename)


def _serve_authorized_file(filename, *, profile=False):
    identity = current_identity()
    if filename != secure_filename(filename):
        raise MutationConflict("Arquivo nao encontrado", 404)
    with get_session() as db:
        if not allowed_file(db, identity, filename, profile=profile):
            raise MutationConflict("Arquivo nao encontrado", 404)
    response = send_from_directory(get_upload_folder(), filename, as_attachment=not profile)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@document_bp.route('/professores/<int:professor_id>/arquivos/upload', methods=['POST'])
def upload_arquivo_professor(professor_id):
    identity = current_identity()
    if not identity.admin:
        return jsonify({"erro": "Acesso permitido apenas para administradores"}), 403

    if "arquivo" not in request.files:
        return jsonify({"erro": "Arquivo nao enviado"}), 400

    arquivo = request.files["arquivo"]
    if not arquivo.filename:
        return jsonify({"erro": "Nome do arquivo nao informado"}), 400

    original_filename = secure_filename(arquivo.filename)
    if not original_filename:
        return jsonify({"erro": "Nome do arquivo invalido"}), 400

    upload_folder = get_upload_folder()
    os.makedirs(upload_folder, exist_ok=True)
    filename = f"{uuid4().hex}_{original_filename}"
    saved_path = os.path.join(upload_folder, filename)

    db = get_session()
    try:
        entry, replay = begin_submission(db, f"documento-professor:{professor_id}", actor=identity.id)
        if replay:
            response, status = replay
            redirect_to = request.form.get("redirect_to")
            if redirect_to and redirect_to.startswith("/") and not redirect_to.startswith("//") and "\\" not in redirect_to:
                return redirect(redirect_to)
            return jsonify(response), status
        professor = db.get(ProfessorModel, professor_id)
        if not professor:
            return jsonify({"erro": "Professor nao encontrado"}), 404

        disciplina = _get_or_create_disciplina_geral(db)
        arquivo.save(saved_path)
        documento = DocumentoModel(
            aluno_id=None,
            professor_id=professor.id,
            disciplina_id=disciplina.id,
            titulo=(request.form.get("titulo") or original_filename)[:150],
            caminho_arquivo=filename,
        )
        db.add(documento)
        finish_submission(db, entry, {"mensagem": "Arquivo enviado"}, 201)
    except Exception:
        db.rollback()
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise
    finally:
        db.close()

    redirect_to = request.form.get("redirect_to")
    if redirect_to and redirect_to.startswith("/") and not redirect_to.startswith("//") and "\\" not in redirect_to:
        return redirect(redirect_to)

    return jsonify({"mensagem": "Arquivo enviado"}), 201


@document_bp.route('/arquivos/perfil/<path:filename>', methods=['GET'])
def perfil_arquivo(filename):
    return _serve_authorized_file(filename, profile=True)
