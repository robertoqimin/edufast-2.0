from flask import Flask, jsonify
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

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
    if app.config["APP_ENV"] == "production":
        if len(app.config["SECRET_KEY"]) < 32 or app.config["SECRET_KEY"] == "desenvolvimento-web-flask":
            raise RuntimeError("Produção exige SECRET_KEY própria com pelo menos 32 caracteres.")
        if not app.config["TRUSTED_HOSTS"]:
            raise RuntimeError("Produção exige TRUSTED_HOSTS.")
        # Um único proxy Caddy. A porta do app não é publicada no Compose de produção.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    init_db()

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
