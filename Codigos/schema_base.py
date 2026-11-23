"""Criacao do esquema completo em banco VAZIO, ja registrado na versao mais recente (A3).

PostgreSQL: executa o arquivo revisavel ``migrations/base/esquema_vN.sql`` (transacional).
SQLite (somente testes e demonstracoes em memoria): ``create_all`` dos modelos com o
mesmo registro de versoes, para que todos os caminhos terminem no mesmo estado.

Recusa qualquer banco que ja tenha tabelas: nunca migra, limpa ou completa esquema existente.
"""
from schema_inventory import ESCOLA_DIR, load_migrations

ORIGEM = 'aplicada'


def versao_base(migrations=None):
    migrations = migrations if migrations is not None else load_migrations()
    return max(item['versao'] for item in migrations)


def arquivo_base(migrations=None):
    """Caminho relativo a migrations/, gravado no registro de quem nasceu pela base."""
    return f'base/esquema_v{versao_base(migrations)}.sql'


def linhas_registro_base(migrations=None):
    """Uma linha por proposta incorporada a base, todas apontando para o arquivo base."""
    migrations = migrations if migrations is not None else load_migrations()
    arquivo = arquivo_base(migrations)
    return [{'versao': item['versao'], 'descricao': item['arquivo'][4:-4], 'arquivo': arquivo, 'origem': ORIGEM}
            for item in migrations]


def executar_arquivo_postgresql(engine, sql, schema=None):
    """Executa um arquivo SQL inteiro como o psql faria; o proprio arquivo controla BEGIN/COMMIT.

    A conexao volta ao pool sempre no estado normal (sem autocommit e sem search_path
    alterado), inclusive em caso de erro: do contrario, sessoes seguintes perderiam
    transacoes e SAVEPOINT. ``schema`` deve ser um identificador fixo do chamador.
    """
    raw = engine.raw_connection()
    try:
        raw.driver_connection.autocommit = True
        with raw.driver_connection.cursor() as cursor:
            try:
                if schema:
                    cursor.execute(f'SET search_path TO {schema}')
                cursor.execute(sql)
            except Exception:
                cursor.execute('ROLLBACK')
                raise
            finally:
                if schema:
                    cursor.execute('RESET search_path')
    finally:
        raw.driver_connection.autocommit = False
        raw.close()


def criar_esquema_base(engine):
    """Cria o esquema completo e registrado; recusa banco que ja tenha qualquer tabela."""
    from sqlalchemy import inspect, text
    existentes = inspect(engine).get_table_names()
    if existentes:
        raise RuntimeError('Banco ja contem tabelas; o esquema base so e criado em banco vazio. Nada foi alterado.')
    if engine.dialect.name == 'postgresql':
        caminho = ESCOLA_DIR / arquivo_base()
        if not caminho.is_file():
            raise RuntimeError(f'Esquema base ausente nesta release: {caminho.name}')
        executar_arquivo_postgresql(engine, caminho.read_text(encoding='utf-8'))
    elif engine.dialect.name == 'sqlite':
        from app.database import Base
        from app import models  # noqa: F401 — registra todas as tabelas
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text('INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem) '
                                    'VALUES (:versao, :descricao, :arquivo, :origem)'), linhas_registro_base())
    else:
        raise RuntimeError(f'Banco nao suportado para o esquema base: {engine.dialect.name}')
    return versao_base()
