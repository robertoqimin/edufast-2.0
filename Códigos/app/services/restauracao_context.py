"""Reuse restored domain handlers inside the single approval transaction.

Nested handlers may flush, but never commit or close the caller's session.
Validation uses a rollback-only savepoint; approval executes the same validations
against current links and versions before the outer approval commits.
"""
from contextvars import ContextVar
import json
import hashlib
from flask import current_app, session, url_for
from werkzeug.exceptions import HTTPException
from app.database import get_session as open_session
from app.concurrency import MutationConflict

_transaction = ContextVar('restored_transaction', default=None)
_principal = ContextVar('restored_principal', default=None)
MATERIAL_ACTIONS = frozenset({'cursos.criar', 'cursos.editar_estrutura', 'cursos.duplicar', 'cursos.estado'})
ALLOWED_ACTIONS = MATERIAL_ACTIONS | {'academico.criar_avaliacao', 'academico.lancar',
                                     'academico.publicar', 'academico.configurar_avaliacao'}
FIELDS = {
    'cursos.criar': {'disciplina_id', 'titulo', 'descricao'},
    'cursos.editar_estrutura': {'acao', 'tipo', 'pai_id', 'id', 'titulo', 'descricao', 'video'},
    'cursos.duplicar': set(), 'cursos.estado': {'estado'},
    'academico.criar_avaliacao': {'turma_disciplina_id', 'periodo_id', 'titulo', 'peso'},
    'academico.lancar': {'valor', 'observacao', 'versao'},
    'academico.publicar': set(), 'academico.configurar_avaliacao': {'acao', 'titulo', 'peso'},
}


class _SessionProxy:
    def __init__(self, db): self.db = db
    def __getattr__(self, key): return getattr(self.db, key)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def commit(self): self.db.flush()
    def close(self): pass
    def rollback(self): raise MutationConflict('A operacao conflitou; nenhuma alteracao aplicada')


def get_session():
    db = _transaction.get()
    return _SessionProxy(db) if db is not None else open_session()


def get_identity():
    from app.services.identidade_service import current_identity
    return _principal.get() or current_identity()


def _snapshot(db, operation):
    """Pending edits must not silently overwrite a later administrative edit."""
    from app.models import CursoModel, AvaliacaoModel, LancamentoNotaModel
    params = operation['params']
    if 'curso_id' in params:
        from app.services.cursos import estrutura
        row = db.query(CursoModel).filter_by(id=params['curso_id']).with_for_update().first()
        if row is None:
            raise MutationConflict('Curso nao encontrado', 404)
        values = {'curso': {c.name: getattr(row, c.name) for c in CursoModel.__table__.columns},
                  'estrutura': estrutura(db, row.id)}
    elif 'avaliacao_id' in params:
        row = db.query(AvaliacaoModel).filter_by(id=params['avaliacao_id']).with_for_update().first()
        if row is None:
            raise MutationConflict('Avaliacao nao encontrada', 404)
        notes = db.query(LancamentoNotaModel).filter_by(avaliacao_id=row.id).order_by(LancamentoNotaModel.id).all()
        values = {'avaliacao': {c.name: getattr(row, c.name) for c in AvaliacaoModel.__table__.columns},
                  'notas': [{c.name: getattr(n, c.name) for c in LancamentoNotaModel.__table__.columns} for n in notes]}
    else:
        return None
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode('utf-8')).hexdigest()


def execute(db, user_id, operation, *, validate=False):
    from app.models import UsuarioModel
    endpoint, params, payload = operation.get('endpoint'), operation.get('params'), operation.get('payload')
    if not isinstance(endpoint, str) or endpoint not in ALLOWED_ACTIONS or not isinstance(params, dict) or not isinstance(payload, dict):
        raise MutationConflict('Operacao nao permitida', 400)
    if set(payload) - FIELDS[endpoint] or len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) > 50000:
        raise MutationConflict('Campos nao permitidos ou conteudo muito grande', 400)
    rule = next((r for r in current_app.url_map.iter_rules(endpoint) if 'POST' in r.methods), None)
    if rule is None or set(params) != rule.arguments:
        raise MutationConflict('Parametros da operacao invalidos', 400)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in params.values()):
        raise MutationConflict('Recurso invalido', 400)
    user = db.get(UsuarioModel, user_id)
    if not user or user.tipo != 'professor' or user.estado != 'ativo':
        raise MutationConflict('Professor sem acesso ativo', 403)
    # Build only registered, allowlisted routes. No user-controlled URL dispatch.
    try:
        path = url_for(endpoint, **params)
    except Exception:
        raise MutationConflict('Parametros da operacao invalidos', 400)
    from app.services.identidade_service import Identidade
    token = _transaction.set(db)
    principal_token = _principal.set(Identidade(user.id, user.tipo, user.revisor_materiais, user.auth_version))
    nested = None
    try:
        if validate:
            nested = db.begin_nested()
        snapshot = _snapshot(db, operation)
        if validate:
            operation['_snapshot'] = snapshot
        elif operation.get('_snapshot') != snapshot:
            raise MutationConflict('O conteudo mudou desde o envio; revise antes de aprovar')
        with current_app.test_request_context(path, method='POST', json=payload):
            session.update(user_id=user.id, user_role=user.tipo, user_email=user.email, auth_version=user.auth_version)
            response = current_app.make_response(current_app.view_functions[endpoint](**params))
            if response.status_code >= 400:
                raise MutationConflict('A operacao nao pode ser aplicada', response.status_code)
        db.flush()
    except HTTPException as error:
        raise MutationConflict(error.description, error.code)
    finally:
        if nested is not None and nested.is_active:
            nested.rollback()
        _transaction.reset(token)
        _principal.reset(principal_token)


def material_discipline(db, operation):
    from app.models import CursoModel
    if operation.get('endpoint') not in MATERIAL_ACTIONS:
        return None
    if operation['endpoint'] == 'cursos.criar':
        try: return int(operation['payload'].get('disciplina_id'))
        except (ValueError, TypeError): return None
    row = db.get(CursoModel, operation.get('params', {}).get('curso_id'))
    return row.disciplina_id if row else None
