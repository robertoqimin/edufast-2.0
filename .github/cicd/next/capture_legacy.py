"""Captura revisável do esquema legado; NÃO executar novamente após implementar migrações."""
import json
from pathlib import Path

from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import mysql, sqlite
from app.database import Base
from app import models  # noqa: F401


def main():
    target = Path(__file__).with_name('legacy')
    target.mkdir(exist_ok=True)
    for name, dialect in [('sqlite', sqlite.dialect()), ('mysql', mysql.dialect())]:
        statements = []
        for table in Base.metadata.sorted_tables:
            statements.append(str(CreateTable(table).compile(dialect=dialect)))
            statements += [str(CreateIndex(index).compile(dialect=dialect)) for index in table.indexes]
        (target/(name+'.json')).write_text(json.dumps({'source_commit': '1f034fae6df04c7d17af0e1054da694d3bfad799', 'statements': statements}, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Snapshots legados gerados; revisar e preservar no Git.')


if __name__ == '__main__':
    main()
