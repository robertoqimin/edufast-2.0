"""Criacao do esquema completo em banco VAZIO, ja registrado na versao mais recente (A3).

PostgreSQL: executa o arquivo revisavel ``migrations/base/esquema_vN.sql`` (transacional).
SQLite (somente testes e demonstracoes em memoria): ``create_all`` dos modelos com o
mesmo registro de versoes, para que todos os caminhos terminem no mesmo estado.

Recusa qualquer banco que ja tenha tabelas: nunca migra, limpa ou completa esquema existente.
"""
import re

from schema_inventory import ESCOLA_DIR, checksum_arquivo, load_migrations

ORIGEM = 'aplicada'
_ARQUIVO_SEGURO = re.compile(r'^(?:base/)?[a-z0-9_]+\.sql$')
_CHECKSUM = re.compile(r'^[0-9a-f]{64}$')


def corpo_transacional(sql):
    """Conteudo entre a unica linha 'BEGIN;' e a ultima linha 'COMMIT;' de uma proposta.

    Permite executar o arquivo numa transacao maior, junto com o registro da versao.
    Recusa arquivos fora do formato esperado em vez de adivinhar onde a transacao comeca.
    """
    linhas = sql.replace('\r\n', '\n').split('\n')
    inicios = [i for i, linha in enumerate(linhas) if linha.strip() == 'BEGIN;']
    fins = [i for i, linha in enumerate(linhas) if linha.strip() == 'COMMIT;']
    conteudo = [i for i, linha in enumerate(linhas) if linha.strip() and not linha.strip().startswith('--')]
    if len(inicios) != 1 or len(fins) != 1 or not conteudo or conteudo[0] != inicios[0] or conteudo[-1] != fins[0]:
        raise RuntimeError('Arquivo fora do formato revisado: esperado um unico BEGIN; inicial e COMMIT; final.')
    return '\n'.join(linhas[inicios[0] + 1:fins[0]])


def literal_registro(valor, tipo):
    """Literal SQL apenas para valores do registro, validados por formato (sem entrada livre)."""
    if tipo == 'versao':
        return str(int(valor))
    padrao = {'arquivo': _ARQUIVO_SEGURO, 'checksum': _CHECKSUM, 'descricao': re.compile(r'^[a-z0-9_]+$')}[tipo]
    if not padrao.match(str(valor)):
        raise RuntimeError(f'Valor invalido para o registro ({tipo}).')
    return "'" + str(valor) + "'"


def sql_checksum_base(arquivo, checksum):
    """Grava o checksum do arquivo base em todas as versoes que ele incorporou."""
    return (f'UPDATE educafast_migracoes SET checksum = {literal_registro(checksum, "checksum")} '
            f'WHERE arquivo = {literal_registro(arquivo, "arquivo")};')


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
    arquivo = arquivo_base()
    caminho = ESCOLA_DIR / arquivo
    if not caminho.is_file():
        raise RuntimeError(f'Esquema base ausente nesta release: {arquivo}')
    checksum = checksum_arquivo(caminho)
    if engine.dialect.name == 'postgresql':
        # Estrutura, registro e checksum na mesma transacao.
        corpo = corpo_transacional(caminho.read_text(encoding='utf-8'))
        executar_arquivo_postgresql(engine, f'BEGIN;\n{corpo}\n{sql_checksum_base(arquivo, checksum)}\nCOMMIT;')
    elif engine.dialect.name == 'sqlite':
        from app.database import Base
        from app import models  # noqa: F401 — registra todas as tabelas
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text('INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem, checksum) '
                                    'VALUES (:versao, :descricao, :arquivo, :origem, :checksum)'),
                               [{**linha, 'checksum': checksum} for linha in linhas_registro_base()])
    else:
        raise RuntimeError(f'Banco nao suportado para o esquema base: {engine.dialect.name}')
    return versao_base()
