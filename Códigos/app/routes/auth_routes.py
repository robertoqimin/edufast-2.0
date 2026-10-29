from flask import Blueprint, jsonify, redirect, request, session, url_for

from app.auth import professor_required
from app.controllers.auth_controller import buscar_alunos, cadastrar_usuario, login_usuario
from app.routes.guards import admin_json_required

auth_bp = Blueprint('auth', __name__)


def _admin_session_required():
    return admin_json_required()


def _get_request_data():
    if request.form:
        return request.form.copy()

    return request.get_json(silent=True) or {}


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    response, status = login_usuario(data)
    if status == 200:
        session["user_id"] = response["id"]
        session["user_email"] = response["email"]
        session["user_role"] = response["role"]
        session["auth_version"] = response["auth_version"]

    return jsonify(response), status


@auth_bp.route('/logout', methods=['GET'])
def logout():
    from app.services.identidade_service import current_identity
    from app.database import get_session
    from app.models import UsuarioModel
    identity = current_identity(required=False)
    if identity:
        with get_session() as db:
            db.query(UsuarioModel).filter_by(id=identity.id).update({UsuarioModel.auth_version: UsuarioModel.auth_version + 1})
            db.commit()
    session.clear()
    return redirect(url_for("home.home"))


@auth_bp.route('/cadastro', methods=['POST'])
def cadastro():
    data = _get_request_data()
    response, status = cadastrar_usuario(data, request.files)
    return jsonify(response), status


@auth_bp.route('/cadastro/aluno', methods=['POST'])
@auth_bp.route('/cadastro/alunos', methods=['POST'])
def cadastro_aluno():
    error_response = _admin_session_required()
    if error_response:
        return error_response

    data = _get_request_data()
    data["tipo"] = "aluno"
    response, status = cadastrar_usuario(data, request.files, aprovado=True)
    return jsonify(response), status


@auth_bp.route('/cadastro/professor', methods=['POST'])
@auth_bp.route('/cadastro/professores', methods=['POST'])
def cadastro_professor():
    error_response = _admin_session_required()
    if error_response:
        return error_response

    data = _get_request_data()
    data["tipo"] = "professor"
    response, status = cadastrar_usuario(data, request.files, aprovado=True)
    return jsonify(response), status


@auth_bp.route('/professor/teste', methods=['GET'])
@professor_required
def teste_professor():
    # Rota simples para validar se o JWT pertence a um professor.
    return jsonify({"mensagem": "Permissao de professor validada"}), 200


@auth_bp.route('/alunos/busca', methods=['GET'])
def alunos_busca():
    from app.services.identidade_service import require_role
    require_role("professor", "admin", "super_admin")
    from app.services.identidade_service import current_identity
    if request.args.get("cpf") is not None and not current_identity().admin:
        return jsonify({"erro": "Busca por CPF restrita a administracao"}), 403
    termo = request.args.get("termo") or request.args.get("q") or request.args.get("cpf")
    response, status = buscar_alunos(termo)
    return jsonify(response), status
