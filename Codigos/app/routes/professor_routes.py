from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from app.controllers.professor_controller import (
    get_teacher_area_data,
    launch_activity,
    upload_requested_document,
)
from app.routes.guards import teacher_required

professor_bp = Blueprint("professor", __name__)


@professor_bp.route("/professor", methods=["GET"])
@professor_bp.route("/professor/dashboard", methods=["GET"])
def dashboard():
    identity = teacher_required()
    data = get_teacher_area_data(identity.id)
    if not data:
        abort(404)

    return render_template("professor_painel.html", **data)


@professor_bp.route("/professor/notas/salvar", methods=["POST"])
def salvar_nota():
    """Aposentada na B1: notas são lançadas no diário da avaliação, com aprovação."""
    teacher_required()
    return jsonify({"erro": "Notas agora sao lancadas no diario da avaliacao.",
                    "destino": url_for("academico.painel")}), 410


@professor_bp.route("/professor/atividades/lancar", methods=["POST"])
def lancar_atividade():
    identity = teacher_required()
    response, status = launch_activity(identity.id, request.form, request.files)
    if 200 <= status < 300:
        return redirect(url_for("professor.dashboard"))

    return jsonify(response), status


@professor_bp.route("/professor/documentos/upload", methods=["POST"])
def upload_documento_professor():
    identity = teacher_required()
    response, status = upload_requested_document(
        identity.id,
        request.form,
        request.files,
    )
    if 200 <= status < 300:
        return redirect(url_for("professor.dashboard"))

    return jsonify(response), status
