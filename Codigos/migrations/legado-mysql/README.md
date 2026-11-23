# Propostas MySQL históricas — não usar

Estes arquivos são as propostas 001–007 escritas para MySQL 8.4, preservadas como
referência após a troca do banco para PostgreSQL em 22/11/2026. Nenhuma delas foi
executada em banco persistente.

As propostas vigentes ficam em `Códigos/migrations/`, em SQL PostgreSQL, geradas por
`migrations/gerar_postgresql.py`. O gerador lê esta pasta apenas para saber quais
tabelas cada proposta cria e em que ordem.

Não aplicar estes arquivos em nenhum banco. Relatório da troca:
`Documentos/testes/MIGRACAO_POSTGRESQL_2026-11-22.md`.
