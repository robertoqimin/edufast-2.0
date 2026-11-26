"""Gera proposta PostgreSQL offline. Não conecta nem executa migrations."""
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateTable
from .models import Base


def proposed_sql():
    tables = '\n\n'.join(
        '\n'.join(line.rstrip() for line in str(CreateTable(table).compile(dialect=dialect())).strip().splitlines()) + ';'
        for table in Base.metadata.sorted_tables)
    return ('-- PROPOSTA: revisar antes de executar, somente no banco CENTRAL vazio.\n'
            '-- PostgreSQL 17. Arquivo transacional (BEGIN/COMMIT): uma falha desfaz a proposta inteira.\n\n'
            'BEGIN;\n\n' + tables + '\n\nCOMMIT;\n')


if __name__ == '__main__':
    print(proposed_sql(), end='')
