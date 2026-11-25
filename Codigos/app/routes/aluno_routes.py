from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from app.controllers.document_controller import upload_requested_document_for_owner
from app.controllers.aluno_controller import (
    get_aluno_disciplina_detail,
    get_aluno_area_data,
    get_aluno_by_user_id,
)
from app.routes.guards import aluno_required
from app.views.respostas import resposta_erro

aluno_bp = Blueprint("aluno", __name__)


@aluno_bp.route("/aluno", methods=["GET"])
@aluno_bp.route("/aluno/dashboard", methods=["GET"])
def dashboard():
    identity = aluno_required()
    data = get_aluno_area_data(identity.id)
    if not data:
        abort(404)

    return render_template("aluno_painel.html", **data)


@aluno_bp.route("/aluno/disciplinas/<int:disciplina_id>", methods=["GET"])
def disciplina_detail(disciplina_id):
    identity = aluno_required()
    data = get_aluno_disciplina_detail(identity.id, disciplina_id)
    if not data:
        abort(404)

    return render_template("aluno_disciplina.html", **data)


@aluno_bp.route("/aluno/documentos/upload", methods=["POST"])
def upload_documento_aluno():
    identity = aluno_required()
    aluno = get_aluno_by_user_id(identity.id)
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado"}), 404

    solicitacao_id = request.form.get("solicitacao_id", type=int)
    if not solicitacao_id:
        return resposta_erro({"erro": "Selecione a solicitação de documento."}, 400)

    response, status = upload_requested_document_for_owner(
        "aluno_id", aluno["id"], solicitacao_id, request.files)
    if 200 <= status < 300:
        return redirect(url_for("aluno.dashboard"))
    return resposta_erro(response, status)
