"""Gera as propostas 001-007 em SQL PostgreSQL, offline, a partir dos modelos.

Nao conecta a nenhum banco e nao executa DDL. A lista e a ordem das tabelas de
cada proposta vem dos arquivos MySQL preservados em ``legado-mysql/``; as
definicoes vem dos modelos SQLAlchemy atuais, compiladas para PostgreSQL.

Uso, em ``Codigos/``: ``python migrations/gerar_postgresql.py`` (reescreve 001-007).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from app.database import Base  # noqa: E402
from app import models  # noqa: E402,F401
from schema_inventory import parse_migration  # noqa: E402

LEGADO = HERE / 'legado-mysql'
CABECALHO = [
    '-- PostgreSQL 17. Arquivo transacional (BEGIN/COMMIT): uma falha desfaz a proposta inteira.',
    '-- Gerado por migrations/gerar_postgresql.py a partir dos modelos; revisar antes de executar.',
    '-- Aplicar com: psql -v ON_ERROR_STOP=1 -f <arquivo>',
]

ANTES = {
    1: ['ALTER TABLE alunos ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;',
        'ALTER TABLE professores ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;',
        'ALTER TABLE notas ADD COLUMN versao INTEGER NOT NULL DEFAULT 1;'],
    2: ['ALTER TABLE usuarios',
        "    ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'ativo',",
        '    ADD COLUMN revisor_materiais BOOLEAN NOT NULL DEFAULT FALSE,',
        '    ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0;'],
    7: ['ALTER TABLE curso_aulas ALTER COLUMN video_id DROP NOT NULL;'],
}

DEPOIS = {
    1: ['-- Constraints antigas ausentes precisam de DDL separado revisado apos preflight.',
        '-- Este arquivo nao elimina nem consolida registros antigos.'],
    2: ['-- Nao ha evidencia no legado que diferencie docente criado por admin de autoinscricao.',
        '-- Revisar esta quarentena e uma allowlist comprovada ANTES de rodar; nao aprovar todos.',
        'INSERT INTO solicitacoes_alteracoes (solicitante_id, tipo, payload, estado, recurso_pendente)',
        "SELECT id, 'cadastro', json_build_object('usuario_id', id, 'papel_solicitado', 'professor')::text,",
        "       'pendente', 'cadastro:' || id",
        "FROM usuarios WHERE LOWER(tipo) = 'professor';",
        "UPDATE usuarios SET estado = 'pendente', revisor_materiais = FALSE,",
        '                    auth_version = auth_version + 1',
        "WHERE LOWER(tipo) = 'professor';",
        '-- Nao promove nenhum usuario a super_admin. Provisionar conta NOVA via CLI autorizada.'],
}

# Estado original de colunas que uma proposta posterior altera.
ORIGINAL = {3: {('curso_aulas', 'video_id'): ('video_id VARCHAR(11),', 'video_id VARCHAR(11) NOT NULL,')}}


def _comentarios(texto):
    linhas = []
    for linha in texto.splitlines():
        if not linha.startswith('--'):
            break
        if 'MySQL' not in linha and 'DDL' not in linha:
            linhas.append(linha)
    return linhas


def _tabela(nome, versao):
    table = Base.metadata.tables[nome]
    dialect = postgresql.dialect()
    ddl = '\n'.join(l.rstrip() for l in str(CreateTable(table).compile(dialect=dialect)).strip().splitlines())
    for (alvo, _coluna), (atual, original) in ORIGINAL.get(versao, {}).items():
        if alvo == nome:
            if atual not in ddl:
                raise RuntimeError(f'Coluna original nao encontrada em {nome}: {atual}')
            ddl = ddl.replace(atual, original)
    partes = [ddl + ';']
    for index in sorted(table.indexes, key=lambda i: i.name):
        partes.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ';')
    return '\n'.join(partes)


def gerar(caminho_legado):
    versao = int(caminho_legado.name[:3])
    texto = caminho_legado.read_text(encoding='utf-8')
    corpo = [*_comentarios(texto), *CABECALHO, '', 'BEGIN;', '']
    if versao in ANTES:
        corpo += [*ANTES[versao], '']
    for nome in parse_migration(texto)['tables']:
        corpo += [_tabela(nome, versao), '']
    if versao in DEPOIS:
        corpo += [*DEPOIS[versao], '']
    corpo.append('COMMIT;')
    return '\n'.join(corpo) + '\n'


def main():
    for caminho in sorted(LEGADO.glob('[0-9][0-9][0-9]_*.sql')):
        (HERE / caminho.name).write_text(gerar(caminho), encoding='utf-8', newline='\n')
        print('gerado', caminho.name)


if __name__ == '__main__':
    main()
