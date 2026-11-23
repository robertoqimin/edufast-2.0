"""Banco legado com dados ficticios, anterior a todas as propostas (A4).

Somente para bancos descartaveis. O esquema legado sao as tabelas que nenhuma proposta
cria, sem as colunas que as propostas acrescentam. Os dados entram por SQL com as colunas
da epoca, porque os modelos atuais ja conhecem colunas que o legado nao tem.
"""
from sqlalchemy import text

from app.database import Base
from app import models  # noqa: F401 — registra todas as tabelas
from schema_inventory import load_migrations

DOCUMENTO = 'documento_legado_aluno.pdf'
DOCUMENTO_BYTES = b'%PDF-1.4\n% documento ficticio do ensaio\n'

DADOS = [
    "INSERT INTO usuarios (id, email, senha, tipo) VALUES "
    "(1, 'admin@legado.test', :hash, 'admin'), (2, 'aluna@legado.test', :hash, 'aluno'), "
    "(3, 'professor@legado.test', :hash, 'professor'), (4, 'Misto@Legado.test', :hash, 'aluno')",
    "INSERT INTO alunos (id, usuario_id, nome, matricula) VALUES (1, 2, 'Aluna Legada', 'LEG-001'), "
    "(2, 4, 'Aluno Misto', 'LEG-002')",
    "INSERT INTO professores (id, usuario_id, nome, cpf) VALUES (1, 3, 'Professor Legado', '00000000191')",
    "INSERT INTO turmas (id, nome, codigo, ano_letivo) VALUES (1, 'Turma Legada', 'LEG-T1', 2025)",
    "INSERT INTO disciplinas (id, nome, codigo, carga_horaria) VALUES (1, 'Matematica', 'LEG-MAT', 80)",
    "INSERT INTO alunos_turmas (aluno_id, turma_id) VALUES (1, 1), (2, 1)",
    "INSERT INTO alunos_disciplinas (aluno_id, disciplina_id) VALUES (1, 1), (2, 1)",
    "INSERT INTO professores_turmas (professor_id, turma_id) VALUES (1, 1)",
    "INSERT INTO professores_disciplinas (professor_id, disciplina_id) VALUES (1, 1)",
    "INSERT INTO turmas_disciplinas (turma_id, disciplina_id) VALUES (1, 1)",
    "INSERT INTO notas (aluno_id, disciplina_id, professor_id, nota) VALUES (1, 1, 1, 8.75)",
    f"INSERT INTO documentos (aluno_id, disciplina_id, titulo, caminho_arquivo) VALUES (1, 1, 'Historico', '{DOCUMENTO}')",
]

# Retrato comparavel antes/depois: colunas que nenhuma proposta altera.
RETRATO = {
    'usuarios': 'SELECT id, email, senha, tipo FROM usuarios ORDER BY id',
    'alunos': 'SELECT id, usuario_id, nome, matricula FROM alunos ORDER BY id',
    'professores': 'SELECT id, usuario_id, nome, cpf FROM professores ORDER BY id',
    'turmas': 'SELECT id, nome, codigo, ano_letivo FROM turmas ORDER BY id',
    'disciplinas': 'SELECT id, nome, codigo, carga_horaria FROM disciplinas ORDER BY id',
    'vinculos': "SELECT 'at', aluno_id, turma_id FROM alunos_turmas UNION ALL "
                "SELECT 'pd', professor_id, disciplina_id FROM professores_disciplinas ORDER BY 1, 2, 3",
    'notas': 'SELECT aluno_id, disciplina_id, professor_id, CAST(nota AS TEXT) FROM notas ORDER BY id',
    'documentos': 'SELECT aluno_id, disciplina_id, titulo, caminho_arquivo FROM documentos ORDER BY id',
}


def tabelas_legadas():
    criadas = {t for m in load_migrations() for t in m['tables']}
    return [t for t in Base.metadata.sorted_tables if t.name not in criadas]


def criar_legado(engine):
    """Esquema anterior a 001 em banco vazio (as colunas das propostas sao removidas)."""
    legado = tabelas_legadas()
    nomes = {t.name for t in legado}
    Base.metadata.create_all(engine, tables=legado)
    with engine.begin() as connection:
        for migration in load_migrations():
            for table, column in migration['columns']:
                if table in nomes:
                    connection.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))


def popular_legado(engine, senha_hash='hash-ficticio'):
    with engine.begin() as connection:
        for comando in DADOS:
            connection.execute(text(comando), {'hash': senha_hash})
        # Sequencias alinhadas como estariam num banco legado em uso (IDs gerados pelo banco).
        for tabela in ('usuarios', 'alunos', 'professores', 'turmas', 'disciplinas'):
            connection.execute(text(f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
                                    f"(SELECT max(id) FROM {tabela}))"))


def retrato(engine):
    with engine.connect() as connection:
        return {nome: [tuple(r) for r in connection.execute(text(sql))] for nome, sql in RETRATO.items()}
