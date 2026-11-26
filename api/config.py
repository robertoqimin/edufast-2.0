import os
from pathlib import Path

from dotenv import load_dotenv
from runtime_limits import bounded_int

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def caminho_uploads(valor=None):
    """Pasta de arquivos sempre absoluta, ancorada em api/.

    Um caminho relativo era resolvido de formas diferentes: os.path/Path usavam a
    pasta de onde o processo foi iniciado e send_from_directory usava app/. O mesmo
    arquivo podia ser gravado num lugar e procurado em outro.
    """
    caminho = Path(valor or "uploads").expanduser()
    return str(caminho if caminho.is_absolute() else (BASE_DIR / caminho).resolve())


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", "")
    LGPD_CONTROLADOR = os.getenv("LGPD_CONTROLADOR", "Administracao da escola")
    LGPD_CONTATO = os.getenv("LGPD_CONTATO", "Consulte a secretaria da escola")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    BIND_HOST = os.getenv("FLASK_BIND_HOST", "127.0.0.1")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))
    UPLOAD_FOLDER = caminho_uploads(os.getenv("UPLOAD_FOLDER"))
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "app_web")
    DB_URL = os.getenv("DB_URL")
    SESSION_COOKIE_SECURE = APP_ENV == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session")
    TRUSTED_HOSTS = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()] or None
    MAX_CONTENT_LENGTH = bounded_int("MAX_REQUEST_MB", 16, 1, 16) * 1024 * 1024
    MAX_FORM_MEMORY_SIZE = 500_000
    MAX_FORM_PARTS = 100
    DB_POOL_SIZE = bounded_int("DB_POOL_SIZE", 4, 1, 32)
    LOGIN_MAX_TENTATIVAS = bounded_int("LOGIN_MAX_TENTATIVAS", 5, 3, 20)
    LOGIN_MAX_TENTATIVAS_IP = bounded_int("LOGIN_MAX_TENTATIVAS_IP", 30, 10, 500)
    LOGIN_BLOQUEIO_MINUTOS = bounded_int("LOGIN_BLOQUEIO_MINUTOS", 15, 1, 1440)
    DB_MAX_OVERFLOW = bounded_int("DB_MAX_OVERFLOW", 0, 0, 16)
    DB_POOL_TIMEOUT = bounded_int("DB_POOL_TIMEOUT", 5, 1, 30)
    DB_POOL_RECYCLE = bounded_int("DB_POOL_RECYCLE", 1800, 60, 7200)
    RELEASE_ID = os.getenv("RELEASE_ID", "development")

    SQLALCHEMY_DATABASE_URI = DB_URL or (
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
