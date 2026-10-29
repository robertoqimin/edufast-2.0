from flask import jsonify
from app.concurrency import MutationConflict
from app.services.identidade_service import ADMIN_ROLES, require_role


def admin_required():
    return require_role(*ADMIN_ROLES)


def admin_json_required():
    try:
        admin_required()
    except MutationConflict as error:
        return jsonify({"erro": error.message}), error.status
    return None


def aluno_required():
    return require_role("aluno")


def teacher_required():
    return require_role("professor")
