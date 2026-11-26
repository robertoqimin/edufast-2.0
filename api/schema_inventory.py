"""Inventario somente leitura das migrations propostas presentes em um banco.

Le os arquivos ``NNN_*.sql`` para descobrir o que cada proposta cria e compara
com a estrutura real do banco. Nunca executa DDL, nunca altera dados e nunca usa
o ``.env`` como destino: o banco precisa ser informado explicitamente.

A deteccao e estrutural (tabelas, colunas, indices, nulabilidade e regras CHECK
acrescentadas com ADD CONSTRAINT, como na 009). Alteracoes
somente de dados, como a quarentena de professores da 002, nao sao detectaveis.
"""
import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ESCOLA_DIR = BASE_DIR / 'migrations'
CENTRAL_DIR = BASE_DIR / 'control_plane' / 'migrations'

_ARQUIVO = re.compile(r'^(\d{3})_[\w-]+\.sql$')
_COMENTARIO = re.compile(r'--[^\n]*')
_CREATE_TABLE = re.compile(r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', re.I)
_CREATE_INDEX = re.compile(r'\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+`?(\w+)`?\s+ON\s+`?(\w+)`?', re.I)
_ALTER_TABLE = re.compile(r'\bALTER\s+TABLE\s+`?(\w+)`?(.*?);', re.I | re.S)
_ADD_COLUMN = re.compile(r'\bADD\s+COLUMN\s+`?(\w+)`?', re.I)
_MODIFY_COLUMN = re.compile(r'\bMODIFY\s+COLUMN\s+`?(\w+)`?([^,;]*)', re.I)
_NULLABLE = re.compile(r'(?<!NOT\s)\bNULL\b', re.I)
_ADD_CONSTRAINT = re.compile(r'\bADD\s+CONSTRAINT\s+`?(\w+)`?', re.I)
_DROP_NOT_NULL = re.compile(r'\bALTER\s+COLUMN\s+`?(\w+)`?\s+DROP\s+NOT\s+NULL', re.I)

APLICADA, PARCIAL, AUSENTE = 'aplicada', 'parcial', 'ausente'


def parse_migration(sql):
    """Extrai as estruturas que uma migration cria, sem interpretar dados."""
    sql = _COMENTARIO.sub('', sql)
    tables = _CREATE_TABLE.findall(sql)
    indexes = [(table, name) for name, table in _CREATE_INDEX.findall(sql)]
    columns, nullable, constraints = [], [], []
    for table, body in _ALTER_TABLE.findall(sql):
        columns += [(table, column) for column in _ADD_COLUMN.findall(body)]
        constraints += [(table, name) for name in _ADD_CONSTRAINT.findall(body)]
        for column, definition in _MODIFY_COLUMN.findall(body):
            if _NULLABLE.search(definition):
                nullable.append((table, column))
        nullable += [(table, column) for column in _DROP_NOT_NULL.findall(body)]
    return {'tables': tables, 'columns': columns, 'indexes': indexes, 'nullable': nullable, 'constraints': constraints}


def load_migrations(directory=ESCOLA_DIR):
    """Retorna as propostas ``NNN_nome.sql`` do diretorio, em ordem de versao."""
    found = []
    for path in sorted(Path(directory).iterdir()):
        match = _ARQUIVO.match(path.name)
        if match:
            found.append({'versao': int(match.group(1)), 'arquivo': path.name,
                          **parse_migration(path.read_text(encoding='utf-8'))})
    versions = [item['versao'] for item in found]
    if len(versions) != len(set(versions)):
        raise ValueError(f'Versoes de migration duplicadas em {directory}')
    return found


def _checks(migration, snapshot):
    tables = snapshot['tables']
    for table in migration['tables']:
        yield f'tabela {table}', table in tables
    for table, column in migration['columns']:
        yield f'coluna {table}.{column}', column in tables.get(table, {}).get('columns', {})
    for table, index in migration['indexes']:
        yield f'indice {table}.{index}', index in tables.get(table, {}).get('indexes', set())
    for table, column in migration['nullable']:
        yield (f'coluna {table}.{column} aceita nulo',
               tables.get(table, {}).get('columns', {}).get(column) is True)
    for table, name in migration.get('constraints', []):
        yield f'regra {table}.{name}', name in tables.get(table, {}).get('constraints', set())


def classify(migrations, snapshot, registered=None):
    """Compara as propostas com um retrato do banco; funcao pura, sem conexao."""
    items = []
    for migration in migrations:
        checks = list(_checks(migration, snapshot))
        missing = [name for name, present in checks if not present]
        if not checks:
            status = None
        elif not missing:
            status = APLICADA
        elif len(missing) == len(checks):
            status = AUSENTE
        else:
            status = PARCIAL
        item = {'versao': migration['versao'], 'arquivo': migration['arquivo'],
                'situacao': status or 'sem estrutura detectavel', 'verificacoes': len(checks)}
        if status == PARCIAL:
            item['faltando'] = missing
        items.append(item)

    contiguous = 0
    for item in items:
        if item['situacao'] != APLICADA:
            break
        contiguous = item['versao']
    alerts = [f"{item['arquivo']} esta parcial: inspecionar antes de qualquer repeticao"
              for item in items if item['situacao'] == PARCIAL]
    alerts += [f"{item['arquivo']} aparece aplicada depois de uma versao anterior ausente ou parcial"
               for item in items if item['situacao'] == APLICADA and item['versao'] > contiguous]
    report = {'somente_leitura': True, 'versao_estrutural': contiguous,
              'migrations': items, 'alertas': alerts}
    if registered is not None:
        report['versoes_registradas'] = sorted(registered)
        detected = {item['versao'] for item in items if item['situacao'] == APLICADA}
        divergent = sorted(set(registered) ^ detected)
        if divergent:
            report['alertas'].append(
                'Registro em educafast_migracoes difere da estrutura detectada nas versoes '
                + ', '.join(str(v) for v in divergent))
    return report


def checksum_arquivo(path):
    """SHA-256 do conteudo do arquivo com quebras de linha normalizadas (Git pode usar CRLF)."""
    import hashlib
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def problemas_registro(linhas, migrations, directory=ESCOLA_DIR):
    """Inconsistencias que impedem usar o banco com esta versao do codigo; funcao pura."""
    problemas = []
    conhecida = max((m['versao'] for m in migrations), default=0)
    for linha in sorted(linhas, key=lambda item: item['versao']):
        versao = linha['versao']
        if versao > conhecida:
            problemas.append(f'Banco registra a migration {versao}, mais nova que esta versao do codigo '
                             f'(ultima conhecida: {conhecida}). Use a release correspondente ao banco.')
            continue
        checksum, arquivo = linha.get('checksum'), linha.get('arquivo')
        if not checksum:
            continue
        caminho = Path(directory) / (arquivo or '')
        if not arquivo or not caminho.is_file():
            problemas.append(f'Migration {versao} registrada com checksum, mas o arquivo {arquivo!r} nao existe nesta release.')
        elif checksum_arquivo(caminho) != checksum:
            problemas.append(f'Migration {versao} ({arquivo}) foi aplicada com conteudo diferente do arquivo desta release.')
    return problemas


def snapshot(engine):
    """Retrato somente leitura de tabelas, colunas (nulabilidade), indices e regras CHECK."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = {}
    for name in inspector.get_table_names():
        tables[name] = {
            'columns': {c['name']: bool(c.get('nullable')) for c in inspector.get_columns(name)},
            'indexes': {i['name'] for i in inspector.get_indexes(name) if i.get('name')},
            'constraints': {c['name'] for c in [*inspector.get_check_constraints(name), *inspector.get_unique_constraints(name),
                                                *inspector.get_foreign_keys(name)] if c.get('name')},
        }
    return {'tables': tables}


def registry_rows(engine, tables):
    """Linhas de educafast_migracoes (com arquivo/checksum apos a 008), ou None sem a tabela."""
    if 'educafast_migracoes' not in tables:
        return None
    from sqlalchemy import text
    columns = tables['educafast_migracoes']['columns']
    selected = ['versao'] + [name for name in ('arquivo', 'checksum') if name in columns]
    with engine.connect() as connection:
        result = connection.execute(text(f"SELECT {', '.join(selected)} FROM educafast_migracoes"))
        return [dict(zip(selected, row)) for row in result]


def registered_versions(engine, tables):
    """Versoes gravadas em educafast_migracoes, ou None quando a tabela nao existe."""
    rows = registry_rows(engine, tables)
    return None if rows is None else [int(row['versao']) for row in rows]


def inventory(engine, directory=ESCOLA_DIR):
    current = snapshot(engine)
    migrations = load_migrations(directory)
    rows = registry_rows(engine, current['tables'])
    report = classify(migrations, current, None if rows is None else [int(r['versao']) for r in rows])
    if rows:
        report['alertas'] += problemas_registro(rows, migrations, directory)
    return report


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if any(arg not in {'--central'} for arg in args):
        raise SystemExit('Uso: python schema_inventory.py [--central]')
    url = os.environ.get('EDUFAST_REVIEW_DB_URL')
    if not url:
        raise SystemExit('Defina EDUFAST_REVIEW_DB_URL explicitamente; .env nao sera usado como destino')
    from sqlalchemy import create_engine
    engine = create_engine(url)
    try:
        print(json.dumps(inventory(engine, CENTRAL_DIR if '--central' in args else ESCOLA_DIR),
                         indent=2, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
