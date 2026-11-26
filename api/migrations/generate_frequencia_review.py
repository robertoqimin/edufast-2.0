"""Gera SQL para revisão, sem conexão com banco ou execução de DDL."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql
from app.database import Base
from app import models
from app.models import frequencia_model

print('-- PROPOSTA 004: frequencia. REVISAR antes de executar. Sem IF NOT EXISTS.')
print('-- Banco/uploads e DATA_ENCRYPTION_KEY devem ter backup recuperavel.')
print('-- Nao cria atribuicoes docentes e nao converte presencas historicas.')
for table in Base.metadata.sorted_tables:
    if table.name.startswith('frequencia_'):
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect())).strip()
        print('\n'.join(line.rstrip() for line in ddl.splitlines()) + ';')
        for index in sorted(table.indexes, key=lambda item: item.name):
            print(str(CreateIndex(index).compile(dialect=postgresql.dialect())).strip() + ';')
