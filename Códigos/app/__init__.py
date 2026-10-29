from flask import Flask, jsonify
from uuid import uuid4
from sqlalchemy.orm.exc import StaleDataError
from .concurrency import MutationConflict
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import request, session
from urllib.parse import urlsplit
from secrets import token_urlsafe
import hmac

from config import Config
from .database import init_db, engine
from . import models  # noqa: F401
from .routes import register_routes


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(Config)
    if app.config["APP_ENV"] != "development" and app.config["DEBUG"]:
        raise RuntimeError("Debug nao permitido neste ambiente.")
    if (len(app.config["SECRET_KEY"]) < 32 or app.config["SECRET_KEY"] == "desenvolvimento-web-flask"
            or app.config["SECRET_KEY"].lower().startswith(("troque-", "substitua_"))):
        raise RuntimeError("SECRET_KEY propria com pelo menos 32 caracteres e obrigatoria em qualquer ambiente.")
    if app.config["APP_ENV"] == "production":
        if len(app.config["SECRET_KEY"]) < 32 or app.config["SECRET_KEY"] == "desenvolvimento-web-flask":
            raise RuntimeError("Produção exige SECRET_KEY própria com pelo menos 32 caracteres.")
        if not app.config["TRUSTED_HOSTS"]:
            raise RuntimeError("Produção exige TRUSTED_HOSTS.")
        # Um único proxy Caddy. A porta do app não é publicada no Compose de produção.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    init_db()

    @app.errorhandler(MutationConflict)
    def mutation_conflict(error):
        return jsonify(erro=error.message), error.status

    @app.errorhandler(StaleDataError)
    def stale_data(error):
        return jsonify(erro="Registro alterado por outro envio; recarregue antes de salvar"), 409

    @app.context_processor
    def submission_context():
        if "csrf_token" not in session:
            session["csrf_token"] = token_urlsafe(32)
        return {"submission_key": lambda: uuid4().hex, "csrf_token": session["csrf_token"]}

    @app.before_request
    def browser_origin_protection():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return
        origin = request.headers.get("Origin")
        if origin:
            expected, supplied = urlsplit(request.host_url), urlsplit(origin)
            if (supplied.scheme, supplied.netloc) != (expected.scheme, expected.netloc):
                return jsonify(erro="Origem nao autorizada"), 403
            if session.get("user_id") and not request.headers.get("Authorization"):
                supplied_token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
                if not hmac.compare_digest(str(session.get("csrf_token", "")), supplied_token) or not supplied_token:
                    return jsonify(erro="Token CSRF obrigatorio"), 403
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            return jsonify(erro="Origem nao autorizada"), 403

    register_routes(app)

    @app.get("/healthz")
    def healthz():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            app.logger.exception("Healthcheck: banco indisponível")
            return jsonify(status="unavailable"), 503
        return jsonify(status="ok", release=app.config["RELEASE_ID"])

    from .commands import register_commands
    register_commands(app)

    return app
