"""Gera proposta MySQL offline. Não conecta nem executa migrations."""
from sqlalchemy.dialects.mysql import dialect
from sqlalchemy.schema import CreateTable
from .models import Base


def proposed_sql():
    return '-- PROPOSTA: revisar antes de executar, somente no banco CENTRAL vazio.\n\n' + '\n\n'.join(
        '\n'.join(line.rstrip() for line in str(CreateTable(table).compile(dialect=dialect())).strip().splitlines()) + ';'
        for table in Base.metadata.sorted_tables) + '\n'


if __name__ == '__main__':
    print(proposed_sql(), end='')
