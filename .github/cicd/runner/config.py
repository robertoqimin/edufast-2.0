import os
from pathlib import Path
import uuid


def create_config(entrypoint):
    ROOT = Path(entrypoint).resolve().parents[2]
    PIPELINE = Path(entrypoint).resolve().parent
    REPORT = ROOT / '.ci-results'
    PROJECT = 'edufast-ci-' + uuid.uuid4().hex[:10]
    IMAGE = PROJECT + ':tested'
    ENV = {**os.environ, 'DOMAIN': 'localhost', 'ACME_EMAIL': 'ci@example.test',
           'SECRET_KEY': 'ci-only-secret-key-with-at-least-32-characters',
           'DB_PASSWORD': 'ci-database-only', 'POSTGRES_ADMIN_PASSWORD': 'ci-root-only',
           'DB_USER': 'edufast', 'DB_NAME': 'edufast', 'EDUFAST_IMAGE': IMAGE}
    COMPOSE = ['docker', 'compose', '-p', PROJECT, '-f', str(PIPELINE/'compose.production.yml'), '-f', str(PIPELINE/'compose.test.yml')]
    return ROOT, PIPELINE, REPORT, PROJECT, IMAGE, ENV, COMPOSE
