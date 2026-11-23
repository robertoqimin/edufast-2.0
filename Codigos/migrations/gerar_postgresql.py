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
# Tabelas cuja forma original difere do modelo atual por colunas/constraints de propostas posteriores.
ORIGINAL_DDL = {(3, 'educafast_migracoes'): 'CREATE TABLE educafast_migracoes (\n\tversao INTEGER NOT NULL,\n\tPRIMARY KEY (versao)\n);'}

REGISTRO = '008_registro_migracoes.sql'
REGISTRO_CABECALHO = [
    '-- PROPOSTA 008: registro de versoes do esquema. REVISAR antes de executar.',
    '-- Completa educafast_migracoes (criada pela 003) e registra como "detectada" cada proposta',
    '-- anterior cuja estrutura completa ja existe. Nao altera outras tabelas nem dados escolares.',
    '-- checksum fica vazio: um arquivo nao contem o proprio hash; o aplicador revisado o preenche.',
    *CABECALHO,
]
REGISTRO_ALTER = [
    'ALTER TABLE educafast_migracoes',
    '    ADD COLUMN descricao VARCHAR(120),',
    '    ADD COLUMN arquivo VARCHAR(120),',
    '    ADD COLUMN checksum VARCHAR(64),',
    '    ADD COLUMN aplicada_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,',
    "    ADD COLUMN origem VARCHAR(12) DEFAULT 'aplicada' NOT NULL,",
    "    ADD CONSTRAINT ck_migracao_origem CHECK (origem IN ('aplicada','detectada')),",
    '    ADD CONSTRAINT ck_migracao_checksum CHECK (checksum IS NULL OR length(checksum) = 64);',
]


def _literal(valor):
    return "'" + valor.replace("'", "''") + "'"


def _condicoes(assinatura):
    coluna = ('EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() '
              'AND table_name = {t} AND column_name = {c}{extra})')
    condicoes = [f'to_regclass({_literal(t)}) IS NOT NULL' for t in assinatura['tables']]
    condicoes += [coluna.format(t=_literal(t), c=_literal(c), extra='') for t, c in assinatura['columns']]
    condicoes += [f'EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() '
                  f'AND tablename = {_literal(t)} AND indexname = {_literal(i)})' for t, i in assinatura['indexes']]
    condicoes += [coluna.format(t=_literal(t), c=_literal(c), extra=" AND is_nullable = 'YES'")
                  for t, c in assinatura['nullable']]
    return condicoes


def gerar_registro():
    """008: registro retroativo derivado das mesmas assinaturas usadas pelo inventario."""
    corpo = [*REGISTRO_CABECALHO, '', 'BEGIN;', '', *REGISTRO_ALTER, '']
    for caminho in sorted(HERE.glob('[0-9][0-9][0-9]_*.sql')):
        versao = int(caminho.name[:3])
        if caminho.name == REGISTRO or versao >= int(REGISTRO[:3]):
            continue
        descricao = caminho.stem[4:]
        condicoes = _condicoes(parse_migration(caminho.read_text(encoding='utf-8')))
        corpo += [f'-- {caminho.name}: registrada somente se toda a estrutura estiver presente.',
                  'INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)',
                  f"SELECT {versao}, {_literal(descricao)}, {_literal(caminho.name)}, 'detectada'",
                  'WHERE ' + '\n  AND '.join(condicoes),
                  'ON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo;', '']
    corpo += ['INSERT INTO educafast_migracoes (versao, descricao, arquivo, origem)',
              f"VALUES ({int(REGISTRO[:3])}, 'registro_migracoes', {_literal(REGISTRO)}, 'aplicada');", '',
              'COMMIT;']
    return '\n'.join(corpo) + '\n'


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
    if (versao, nome) in ORIGINAL_DDL:
        return ORIGINAL_DDL[(versao, nome)]
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


def gerados():
    """Conteudo esperado de cada proposta gerada; usado tambem pelo teste de sincronia."""
    arquivos = {caminho.name: gerar(caminho) for caminho in sorted(LEGADO.glob('[0-9][0-9][0-9]_*.sql'))}
    return arquivos


def main():
    for nome, conteudo in gerados().items():
        (HERE / nome).write_text(conteudo, encoding='utf-8', newline='\n')
        print('gerado', nome)
    (HERE / REGISTRO).write_text(gerar_registro(), encoding='utf-8', newline='\n')
    print('gerado', REGISTRO)


if __name__ == '__main__':
    main()
