import json
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from app.concurrency import MutationConflict
from app.database import get_session
from app.models import AlunoModel, AlunoTurmaModel, ProfessorModel, ProfessorTurmaModel, SolicitacaoAlteracaoModel, UsuarioModel
from app.services.aprovacoes_service import can_review, decide_proposal, submit_proposal
from app.services.identidade_service import current_identity

aprovacoes_bp = Blueprint("aprovacoes", __name__)


def _data():
    data = request.get_json(silent=True) if request.is_json else request.form
    if not isinstance(data, dict):
        raise MutationConflict("Corpo deve ser objeto", 400)
    return data


def _items(identity):
    with get_session() as db:
        query = db.query(SolicitacaoAlteracaoModel)
        if not identity.admin:
            if identity.revisor_materiais:
                query = query.filter((SolicitacaoAlteracaoModel.solicitante_id == identity.id) | (SolicitacaoAlteracaoModel.tipo == "lancar_atividade"))
            else:
                query = query.filter_by(solicitante_id=identity.id)
        rows = query.order_by(SolicitacaoAlteracaoModel.id.desc()).limit(100).all()
        items = []
        for row in rows:
            own = row.solicitante_id == identity.id
            reviewer = can_review(db, identity, row) if not own else False
            if not own and not reviewer:
                continue
            items.append({"id": row.id, "tipo": row.tipo, "estado": row.estado,
                "solicitante_id": row.solicitante_id, "payload": json.loads(row.payload),
                "decidido_por": row.decidido_por, "justificativa": row.justificativa,
                "pode_decidir": reviewer and row.estado == "pendente", "tem_arquivo": bool(row.arquivo)})
            from app.presenters.aprovacoes_presenter import present
            items[-1]['titulo'], items[-1]['campos'] = present(row.tipo, json.loads(row.payload))
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
        raise MutationConflict("Acesso nao autorizado", 403)
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
    return render_template("solicitacoes.html", identity=identity, solicitacoes=_items(identity), alunos=alunos, docentes=docentes)


@aprovacoes_bp.route("/solicitacoes/alteracoes", methods=["GET", "POST"])
def alteracoes():
    identity = current_identity()
    if identity.papel not in {"admin", "super_admin", "professor"}:
        raise MutationConflict("Acesso nao autorizado", 403)
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


@aprovacoes_bp.get("/solicitacoes/alteracoes/<int:proposal_id>/arquivo")
def arquivo(proposal_id):
    from flask import current_app, send_from_directory
    identity = current_identity()
    with get_session() as db:
        row = db.get(SolicitacaoAlteracaoModel, proposal_id)
        if row is None or not row.arquivo:
            raise MutationConflict("Arquivo nao encontrado", 404)
        if row.solicitante_id != identity.id and not can_review(db, identity, row):
            raise MutationConflict("Arquivo nao encontrado", 404)
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], row.arquivo, as_attachment=True)


@aprovacoes_bp.post("/admin/usuarios/<int:user_id>/permissoes")
def permissoes(user_id):
    identity = current_identity()
    if not identity.admin:
        raise MutationConflict("Acesso nao autorizado", 403)
    data = _data() or {}
    if set(data) - {"papel", "revisor_materiais"}:
        raise MutationConflict("Campos nao permitidos", 400)
    with get_session() as db:
        user = db.query(UsuarioModel).filter_by(id=user_id).with_for_update().first()
        if not user or user.estado != "ativo":
            raise MutationConflict("Usuario ativo nao encontrado", 404)
        role = data.get("papel", user.tipo)
        if not isinstance(role, str):
            raise MutationConflict("Papel invalido", 400)
        role = role.lower()
        if user.tipo == 'super_admin' and role != user.tipo:
            raise MutationConflict('O superperfil protegido nao pode ser rebaixado', 403)
        if "papel" in data and (identity.papel != "super_admin" or identity.id == user.id):
            raise MutationConflict("Somente superadmin pode atribuir papeis a outras contas", 403)
        if role not in {"admin", "super_admin", "professor", "aluno"}:
            raise MutationConflict("Papel invalido", 400)
        flag = data.get("revisor_materiais", user.revisor_materiais)
        if flag not in (True, False, "true", "false", "1", "0"):
            raise MutationConflict("Permissao invalida", 400)
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
