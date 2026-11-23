"""Integration boundary for recovered modules and their original design."""
import hmac
from flask import g, jsonify, redirect, request, session, url_for
from sqlalchemy import inspect
from app.database import engine, get_session
from app.concurrency import MutationConflict
from app.services.identidade_service import current_identity
from app.services.escola import IDENTIDADE_PADRAO, identidade_atual

BLUEPRINTS = {'gestao', 'escola', 'cursos', 'academico', 'privacidade'}


def install(app):
    from app.views.error_view import register_error_pages
    register_error_pages(app)
    from app.routes.gestao_routes import gestao_bp
    from app.routes.escola_routes import escola_bp
    from app.routes.curso_routes import cursos_bp
    from app.routes.academico_routes import academico_bp
    from app.routes.privacidade_routes import privacidade_bp
    for blueprint in (gestao_bp, escola_bp, cursos_bp, academico_bp, privacidade_bp):
        app.register_blueprint(blueprint)

    @app.before_request
    def recovered_boundary():
        if request.blueprint not in BLUEPRINTS:
            return
        if not inspect(engine).has_table('escola_identidade'):
            return jsonify(erro='Funcionalidade aguarda provisionamento revisado do banco.'), 503
        if request.endpoint == 'privacidade.aviso':
            return
        identity = current_identity()
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            if not request.headers.get('Authorization'):
                supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
                if not supplied or not hmac.compare_digest(str(session.get('csrf_token', '')), supplied):
                    raise MutationConflict('Token CSRF obrigatorio', 400)
            if (identity.papel == 'professor' and request.blueprint in {'cursos', 'academico'}):
                from app.services.aprovacoes_service import submit_proposal
                payload = request.get_json(silent=True) if request.is_json else request.form.to_dict()
                if not isinstance(payload, dict):
                    raise MutationConflict('Corpo invalido', 400)
                payload = {k: v for k, v in payload.items() if k not in {'csrf_token', 'idempotency_key'}}
                body, status = submit_proposal('operacao_restaurada', {
                    'endpoint': request.endpoint, 'params': dict(request.view_args or {}), 'payload': payload})
                return (jsonify(body), status) if request.is_json else redirect(url_for('aprovacoes.painel'))

    @app.before_request
    def load_workspace():
        if request.endpoint in {'static', 'healthz'}:
            return
        try:
            principal = None if request.endpoint == 'auth.login' else current_identity(required=False)
        except MutationConflict:
            if request.endpoint != 'home.home':
                raise
            session.clear()
            principal = None
        values = {**IDENTIDADE_PADRAO, 'versao': 0, 'texto_botao': '#071923'}
        cursos_ms04 = False
        if inspect(engine).has_table('escola_identidade'):
            with get_session() as db:
                values = identidade_atual(db)
                # B2: com o MS04 habilitado, menus e links de cursos apontam só para /aprendizagem.
                from app.services.cursos_ms04.comum import habilitado
                cursos_ms04 = habilitado(db, required=False)
        g.escola = values
        g.cursos_ms04 = cursos_ms04
        g.workspace_role = principal.papel if principal else None

    @app.context_processor
    def workspace():
        values = getattr(g, 'escola', {**IDENTIDADE_PADRAO, 'versao': 0, 'texto_botao': '#071923'})
        return {'escola': values, 'tema': {'cor_fundo': values['fundo'], 'cor_destaque': values['destaque']},
                'workspace_role': getattr(g, 'workspace_role', None),
                'cursos_ms04': getattr(g, 'cursos_ms04', False)}
