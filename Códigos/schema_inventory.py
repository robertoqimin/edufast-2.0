"""Inventario somente leitura das migrations propostas presentes em um banco.

Le os arquivos ``NNN_*.sql`` para descobrir o que cada proposta cria e compara
com a estrutura real do banco. Nunca executa DDL, nunca altera dados e nunca usa
o ``.env`` como destino: o banco precisa ser informado explicitamente.

A deteccao e estrutural (tabelas, colunas, indices e nulabilidade). Alteracoes
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

APLICADA, PARCIAL, AUSENTE = 'aplicada', 'parcial', 'ausente'


def parse_migration(sql):
    """Extrai as estruturas que uma migration cria, sem interpretar dados."""
    sql = _COMENTARIO.sub('', sql)
    tables = _CREATE_TABLE.findall(sql)
    indexes = [(table, name) for name, table in _CREATE_INDEX.findall(sql)]
    columns, nullable = [], []
    for table, body in _ALTER_TABLE.findall(sql):
        columns += [(table, column) for column in _ADD_COLUMN.findall(body)]
        for column, definition in _MODIFY_COLUMN.findall(body):
            if _NULLABLE.search(definition):
                nullable.append((table, column))
    return {'tables': tables, 'columns': columns, 'indexes': indexes, 'nullable': nullable}


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


def snapshot(engine):
    """Retrato somente leitura de tabelas, colunas (nulabilidade) e indices."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = {}
    for name in inspector.get_table_names():
        tables[name] = {
            'columns': {c['name']: bool(c.get('nullable')) for c in inspector.get_columns(name)},
            'indexes': {i['name'] for i in inspector.get_indexes(name) if i.get('name')},
        }
    return {'tables': tables}


def registered_versions(engine, tables):
    """Versoes gravadas em educafast_migracoes, ou None quando a tabela nao existe."""
    if 'educafast_migracoes' not in tables:
        return None
    from sqlalchemy import text
    with engine.connect() as connection:
        return [int(row[0]) for row in connection.execute(text('SELECT versao FROM educafast_migracoes'))]


def inventory(engine, directory=ESCOLA_DIR):
    current = snapshot(engine)
    return classify(load_migrations(directory), current,
                    registered_versions(engine, current['tables']))


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
