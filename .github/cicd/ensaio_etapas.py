"""Etapas do ensaio de atualizacao (A4), executadas dentro do container descartavel.

Recusa qualquer banco que nao seja o do executor (host db-ensaio, banco edufast_ensaio).
Saida em JSON numa unica linha, lida pelo run_ensaio_atualizacao.py.
"""
import json
import os
import sys
from pathlib import Path

SENHA = 'Ensaio-legado-2026!'


def _engine():
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    url = make_url(os.environ['DB_URL'])
    if (os.environ.get('EDUFAST_ENSAIO') != '1' or url.host != 'db-ensaio'
            or url.database != 'edufast_ensaio' or url.get_backend_name() != 'postgresql'):
        raise SystemExit('Recusado: somente o banco descartavel do ensaio.')
    return create_engine(url)


def legado(engine):
    from werkzeug.security import generate_password_hash
    from legacy_fixture import DOCUMENTO, DOCUMENTO_BYTES, criar_legado, popular_legado
    criar_legado(engine)
    popular_legado(engine, generate_password_hash(SENHA))
    pasta = Path(os.environ['UPLOAD_FOLDER'])
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / DOCUMENTO).write_bytes(DOCUMENTO_BYTES)
    import hashlib
    return {'documento': DOCUMENTO, 'sha256': hashlib.sha256(DOCUMENTO_BYTES).hexdigest()}


def retrato(engine):
    from sqlalchemy import inspect
    from legacy_fixture import retrato as capturar
    from schema_inventory import inventory
    relatorio = inventory(engine)
    return {'dados': capturar(engine), 'versao_estrutural': relatorio['versao_estrutural'],
            'alertas': relatorio['alertas'], 'tabelas': len(inspect(engine).get_table_names())}


def producao(engine):
    from app import database
    database.Config.APP_ENV = 'production'
    database.engine = engine
    database.init_db()
    return {'inicializacao_producao': 'aceita'}


def main():
    etapa = sys.argv[1]
    engine = _engine()
    try:
        resultado = {'legado': legado, 'retrato': retrato, 'producao': producao}[etapa](engine)
    finally:
        engine.dispose()
    print('RESULTADO ' + json.dumps(resultado, default=str))


if __name__ == '__main__':
    main()
