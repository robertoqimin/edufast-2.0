from app.routes.document_routes import document_bp
from app.routes.home_routes import home_blueprint
from app.routes.auth_routes import auth_bp
from app.routes.professor_routes import professor_bp
from app.routes.aluno_routes import aluno_bp
from app.routes.aprovacoes_routes import aprovacoes_bp
from app.routes.frequencia_routes import frequencia_bp
from app.routes.estudo_routes import estudo_bp
from app.routes.cursos_api_routes import cursos_api_bp
from app.routes.cursos_web_routes import cursos_web_bp
from app.routes.video_routes import video_bp


def register_routes(app):
    app.register_blueprint(home_blueprint)
    app.register_blueprint(auth_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(aluno_bp)
    app.register_blueprint(aprovacoes_bp)
    app.register_blueprint(frequencia_bp)
    app.register_blueprint(estudo_bp)
    app.register_blueprint(cursos_api_bp)
    app.register_blueprint(cursos_web_bp)
    app.register_blueprint(video_bp)
