"""Authentication establishes identity; current database state establishes authority."""
from dataclasses import dataclass

from flask import request, session
from app.database import get_session
from app.models import UsuarioModel
from app.concurrency import MutationConflict

ADMIN_ROLES = frozenset({"admin", "super_admin"})


@dataclass(frozen=True)
class Identidade:
    id: int
    papel: str
    revisor_materiais: bool
    auth_version: int

    @property
    def admin(self):
        return self.papel in ADMIN_ROLES


def load_identity(user_id, claimed_role, version):
    try:
        user_id, version = int(user_id), int(version)
    except (TypeError, ValueError):
        raise MutationConflict("Autenticação inválida", 401)
    with get_session() as db:
        user = db.get(UsuarioModel, user_id)
        if (not user or user.estado != "ativo" or user.auth_version != version
                or user.tipo.lower() != str(claimed_role).lower()):
            raise MutationConflict("Acesso revogado ou conta pendente", 401)
        return Identidade(user.id, user.tipo.lower(), bool(user.revisor_materiais), user.auth_version)


def current_identity(*, required=True):
    # Explicit Bearer authentication never inherits privileges from another cookie.
    if request.headers.get("Authorization"):
        from app.auth import decode_token_from_request
        payload, error = decode_token_from_request()
        if error:
            raise MutationConflict("Autenticação inválida", 401)
        return load_identity(payload.get("sub"), payload.get("role"), payload.get("ver", 0))
    if session.get("user_id"):
        return load_identity(session.get("user_id"), session.get("user_role"), session.get("auth_version", 0))
    if required:
        raise MutationConflict("Autenticação obrigatória", 401)
    return None


def require_role(*roles):
    identity = current_identity(required=False)
    if not identity or identity.papel not in roles:
        raise MutationConflict("Acesso não autorizado", 403)
    return identity
