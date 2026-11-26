from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from app.views.respostas import resposta_erro

from app.auth import normalize_role
from app.controllers.admin_controller import (
    associar_professor_disciplina,
    criar_comunicado,
    criar_disciplina,
    get_admin_data,
    get_aluno_detail,
    get_comunicados,
    get_disciplinas_page_data,
    get_professor_detail,
    request_professor_document,
    request_student_document,
    update_professor_data,
    update_student_data,
)
from app.routes.guards import admin_required
from app.views.dashboard_view import render_dashboard
from app.views.home_view import render_home

home_blueprint = Blueprint("home", __name__)


@home_blueprint.route("/", methods=["GET"])
def home():
    from app.services.identidade_service import current_identity
    from app.concurrency import MutationConflict
    try:
        identity = current_identity(required=False)
    except MutationConflict:
        session.clear()
        identity = None
    if identity and identity.admin:
        return redirect(url_for("home.admin_dashboard"))
    if identity and identity.papel == "aluno":
        return redirect(url_for("aluno.dashboard"))
    if identity and identity.papel == "professor":
        return redirect(url_for("professor.dashboard"))

    context = {"title": "Secretaria Escolar DF"}
    return render_home(context)


@home_blueprint.route("/dashboard", methods=["GET"])
@home_blueprint.route("/dashboard.html", methods=["GET"])
@home_blueprint.route("/admin/dashboard", methods=["GET"])
@home_blueprint.route("/admin_painel.html", methods=["GET"])
def admin_dashboard():
    admin_required()
    # U4/O2: checklist de implantação no topo da visão geral (calculado, nada é gravado).
    from flask import g
    from app.database import get_session
    from app.services import primeiros_passos
    from app.services.identidade_service import current_identity
    identity = current_identity()
    with get_session() as db:
        passos = primeiros_passos.resumo(db, identity.papel, getattr(g, 'cursos_ms04', False))
    context = {"title": "Visão geral", **get_admin_data(), "primeiros_passos": passos, "papel": identity.papel}
    return render_dashboard(context)


@home_blueprint.route("/cadastro/alunos", methods=["GET"])
@home_blueprint.route("/cadastro_aluno.html", methods=["GET"])
@home_blueprint.route("/admin/cadastro-alunos", methods=["GET"])
@home_blueprint.route("/admin_cadastro_aluno.html", methods=["GET"])
def admin_cadastro_alunos():
    admin_required()
    return render_template("admin_cadastro_aluno.html")


@home_blueprint.route("/cadastro/professores", methods=["GET"])
@home_blueprint.route("/cadastro_professores.html", methods=["GET"])
@home_blueprint.route("/admin/cadastro-professores", methods=["GET"])
@home_blueprint.route("/admin_cadastro_professores.html", methods=["GET"])
def admin_cadastro_professores():
    admin_required()
    return render_template("admin_cadastro_professores.html")


@home_blueprint.route("/banco-de-dados", methods=["GET"])
@home_blueprint.route("/banco_de_dados.html", methods=["GET"])
@home_blueprint.route("/admin/banco-de-dados", methods=["GET"])
@home_blueprint.route("/admin_banco_dados.html", methods=["GET"])
def admin_banco_dados():
    admin_required()
    return render_template("admin_banco_dados.html", **get_admin_data())


@home_blueprint.route("/comunicados", methods=["GET", "POST"])
@home_blueprint.route("/admin/comunicados", methods=["GET", "POST"])
@home_blueprint.route("/admin_comunicados.html", methods=["GET", "POST"])
def admin_comunicados():
    admin_required()
    error = None

    if request.method == "POST":
        response, status = criar_comunicado(request.form, session.get("user_email"))
        if status == 201:
            return redirect(url_for("home.admin_comunicados"))

        error = response.get("erro")

    return render_template(
        "admin_comunicados.html",
        comunicados=get_comunicados(),
        error=error,
    )


@home_blueprint.route("/disciplinas", methods=["GET", "POST"])
@home_blueprint.route("/admin/disciplinas", methods=["GET", "POST"])
@home_blueprint.route("/admin_disciplinas.html", methods=["GET", "POST"])
def admin_disciplinas():
    admin_required()
    error = None

    if request.method == "POST":
        action = request.form.get("action")
        if action == "associate_teacher":
            response, status = associar_professor_disciplina(request.form)
        else:
            response, status = criar_disciplina(request.form)

        if status == 201:
            return redirect(url_for("home.admin_disciplinas"))

        error = response.get("erro")

    return render_template(
        "admin_disciplinas.html",
        **get_disciplinas_page_data(),
        error=error,
    )


@home_blueprint.route("/turmas", methods=["GET", "POST"])
@home_blueprint.route("/admin/turmas", methods=["GET", "POST"])
@home_blueprint.route("/admin_turmas.html", methods=["GET", "POST"])
def admin_turmas():
    """U5/O3: uma tela de turma. A tela antiga foi unificada em "Turmas" (Gestão acadêmica)."""
    admin_required()
    if request.method == "GET":
        return redirect(url_for("cursos.gestao_turmas"), code=301)
    return resposta_erro({"erro": "Esta tela foi unificada em Turmas. Crie turmas, registre matérias, "
                                  "atribua professores e matricule alunos por lá."}, 410)


@home_blueprint.route("/alunos/<int:aluno_id>", methods=["GET"])
@home_blueprint.route("/detalhes_aluno/<int:aluno_id>", methods=["GET"])
@home_blueprint.route("/admin/alunos/<int:aluno_id>", methods=["GET"])
@home_blueprint.route("/admin_detalhes_aluno/<int:aluno_id>", methods=["GET"])
def admin_detalhes_aluno(aluno_id):
    admin_required()
    return render_template("admin_detalhes_aluno.html", **get_aluno_detail(aluno_id))


@home_blueprint.route("/admin/alunos/<int:aluno_id>/concluir", methods=["POST"])
def admin_concluir_aluno(aluno_id):
    """Unidades: o colégio marca que o aluno concluiu o 3º ano (habilita a subida pelo CPF)."""
    from app.database import get_session
    from app.models import AlunoModel
    from app.services import unidades
    admin_required()
    with get_session() as db:
        aluno = db.get(AlunoModel, aluno_id)
        unidades.exigir(aluno is not None and isinstance(unidades.ativa(), int))
        unidades.concluir_aluno(db, aluno, unidades.ativa())
        db.commit()
    flash("Conclusão registrada: o aluno pode subir para a faculdade pelo CPF.", "success")
    return redirect(url_for("home.admin_detalhes_aluno", aluno_id=aluno_id))


@home_blueprint.route("/admin/alunos/<int:aluno_id>/levar-para-unidade", methods=["POST"])
def admin_levar_aluno_para_unidade(aluno_id):
    """Unidades: subida manual para a faculdade (aluno sem CPF). Só a unidade de origem libera."""
    from app.database import get_session
    from app.models import AlunoModel
    from app.services import unidades
    identity = admin_required()
    try:
        destino_id = int(request.form.get("destino_id") or 0)
    except ValueError:
        destino_id = 0
    with get_session() as db:
        aluno = db.get(AlunoModel, aluno_id)
        unidades.exigir(aluno is not None and isinstance(unidades.ativa(), int))
        unidades.levar_para_unidade(db, aluno, unidades.ativa(), destino_id, identity.id)
        db.commit()
    flash("Aluno levado para a faculdade com o histórico e os documentos.", "success")
    return redirect(url_for("home.admin_detalhes_aluno", aluno_id=aluno_id))


@home_blueprint.route("/admin/alunos/<int:aluno_id>/documentos/solicitar", methods=["POST"])
def admin_solicitar_documento_aluno(aluno_id):
    admin_required()
    response, status = request_student_document(aluno_id, request.form)
    if status >= 400:
        return resposta_erro(response, status)
    return redirect(url_for("home.admin_detalhes_aluno", aluno_id=aluno_id))


@home_blueprint.route("/admin/alunos/<int:aluno_id>/editar", methods=["POST"])
def admin_editar_aluno(aluno_id):
    admin_required()
    response, status = update_student_data(aluno_id, request.form, request.files)
    if status >= 400:
        return resposta_erro(response, status)
    return redirect(url_for("home.admin_detalhes_aluno", aluno_id=aluno_id))


@home_blueprint.route("/professores/<int:professor_id>", methods=["GET"])
@home_blueprint.route("/detalhes_professor/<int:professor_id>", methods=["GET"])
@home_blueprint.route("/admin/professores/<int:professor_id>", methods=["GET"])
@home_blueprint.route("/admin_detalhes_professor/<int:professor_id>", methods=["GET"])
def admin_detalhes_professor(professor_id):
    admin_required()
    return render_template(
        "admin_detalhes_professor.html",
        **get_professor_detail(professor_id),
    )


@home_blueprint.route("/admin/professores/<int:professor_id>/editar", methods=["POST"])
def admin_editar_professor(professor_id):
    admin_required()
    response, status = update_professor_data(professor_id, request.form, request.files)
    if status >= 400:
        return resposta_erro(response, status)
    return redirect(url_for("home.admin_detalhes_professor", professor_id=professor_id))


@home_blueprint.route("/admin/professores/<int:professor_id>/documentos/solicitar", methods=["POST"])
def admin_solicitar_documento_professor(professor_id):
    admin_required()
    response, status = request_professor_document(professor_id, request.form)
    if status >= 400:
        return resposta_erro(response, status)
    return redirect(url_for("home.admin_detalhes_professor", professor_id=professor_id))


@home_blueprint.route("/detalhes_aluno.html", methods=["GET"])
@home_blueprint.route("/admin_detalhes_aluno.html", methods=["GET"])
def admin_detalhes_aluno_legacy():
    admin_required()
    aluno_id = request.args.get("id", type=int)
    return render_template("admin_detalhes_aluno.html", **get_aluno_detail(aluno_id))


@home_blueprint.route("/detalhes_professor.html", methods=["GET"])
@home_blueprint.route("/admin_detalhes_professor.html", methods=["GET"])
def admin_detalhes_professor_legacy():
    admin_required()
    professor_id = request.args.get("id", type=int)
    return render_template(
        "admin_detalhes_professor.html",
        **get_professor_detail(professor_id),
    )
