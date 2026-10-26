"""Autoriza somente SQLite descartável ou o MySQL exclusivo do Compose de testes."""
import os
from pathlib import Path

from sqlalchemy.engine import make_url


def mysql_de_testes():
    return os.environ.get("EDUCAFAST_TEST_MYSQL") == "1"


def validar_mysql(url):
    parsed = make_url(url)
    if not (mysql_de_testes() and parsed.drivername == "mysql+pymysql"
            and parsed.host == "mysql_test" and parsed.database == "educafast_regressao"
            and parsed.username == "testes"):
        raise RuntimeError("Operação permitida somente no MySQL isolado do Compose de testes.")


def configurar_banco_testes():
    # Somente o ambiente de testes recebe esta chave sintetica.
    os.environ["SECRET_KEY"] = "testes-isolados-chave-sintetica-2026-educafast"
    os.environ["DATA_ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    if mysql_de_testes():
        validar_mysql(os.environ.get("DB_URL", ""))
    else:
        os.environ["DB_URL"] = "sqlite:///:memory:"


def pasta_resultados(root):
    subpasta = os.environ.get('EDUCAFAST_REPORTS_DIR')
    if subpasta:
        base = (root / 'Documentos/testes/resultados').resolve()
        destino = (base / Path(subpasta)).resolve()
        if not destino.is_relative_to(base) or destino == base:
            raise RuntimeError('EDUCAFAST_REPORTS_DIR deve ser uma subpasta dos resultados de testes.')
        return destino
    return root / "Documentos/testes/resultados" / ("mysql" if mysql_de_testes() else "")
