"""Authentication establishes identity; current database state establishes authority."""
from dataclasses import dataclass, field

from flask import g, request, session
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
    unidades: tuple = field(default=())      # unidades com acesso (super admin: todas as ativas)
    unidade_ativa: object = None             # int, ou 'todas' (só super admin)

    @property
    def admin(self):
        return self.papel in ADMIN_ROLES


def load_identity(user_id, claimed_role, version, unidade=None):
    try:
        user_id, version = int(user_id), int(version)
    except (TypeError, ValueError):
        raise MutationConflict("Autenticação inválida", 401)
    with get_session() as db:
        user = db.get(UsuarioModel, user_id)
        if (not user or user.estado != "ativo" or user.auth_version != version
                or user.tipo.lower() != str(claimed_role).lower()):
            raise MutationConflict("Acesso revogado ou conta pendente", 401)
        # Unidade ativa: a sessão só PEDE; o vínculo é conferido aqui, a cada requisição.
        from app.services.unidades import resolver_ativa, unidades_da_conta
        permitidas = unidades_da_conta(db, user)
        ativa = resolver_ativa(permitidas, unidade, user.tipo.lower() == 'super_admin')
        g.unidade_ativa, g.unidades_permitidas = ativa, tuple(permitidas)
        return Identidade(user.id, user.tipo.lower(), bool(user.revisor_materiais), user.auth_version,
                          tuple(permitidas), ativa)


def current_identity(*, required=True):
    # Explicit Bearer authentication never inherits privileges from another cookie.
    if request.headers.get("Authorization"):
        from app.auth import decode_token_from_request
        payload, error = decode_token_from_request()
        if error:
            raise MutationConflict("Autenticação inválida", 401)
        return load_identity(payload.get("sub"), payload.get("role"), payload.get("ver", 0),
                             request.headers.get("X-Unidade"))
    if session.get("user_id"):
        return load_identity(session.get("user_id"), session.get("user_role"), session.get("auth_version", 0),
                             session.get("unidade_id"))
    if required:
        raise MutationConflict("Autenticação obrigatória", 401)
    return None


def require_role(*roles):
    identity = current_identity(required=False)
    if not identity or identity.papel not in roles:
        raise MutationConflict("Acesso não autorizado", 403)
    return identity
