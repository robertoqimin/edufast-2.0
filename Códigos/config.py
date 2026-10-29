import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    BIND_HOST = os.getenv("FLASK_BIND_HOST", "127.0.0.1")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "app_web")
    DB_URL = os.getenv("DB_URL")
    SESSION_COOKIE_SECURE = APP_ENV == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    TRUSTED_HOSTS = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "").split(",") if h.strip()] or None
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    RELEASE_ID = os.getenv("RELEASE_ID", "development")

    SQLALCHEMY_DATABASE_URI = DB_URL or (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
