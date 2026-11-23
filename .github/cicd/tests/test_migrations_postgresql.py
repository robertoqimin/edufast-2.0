"""Aplica as propostas PostgreSQL 001-007 sobre o esquema legado, em banco descartavel.

Nunca roda fora do executor descartavel: recria o banco de teste. Compara o
resultado com os modelos e confirma que uma proposta com falha nao deixa estado
parcial (DDL transacional do PostgreSQL).
"""
import json
import os
from unittest import TestCase, skipUnless

from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models  # noqa: F401 — registra todas as tabelas da escola
from schema_inventory import APLICADA, ESCOLA_DIR, inventory, load_migrations

POSTGRES = engine.dialect.name == 'postgresql'
MODELO = 'modelo_esperado'


def run_sql(sql):
    """Executa um arquivo inteiro como o psql faria; o proprio arquivo controla a transacao."""
    raw = engine.raw_connection()
    try:
        raw.driver_connection.autocommit = True
        with raw.driver_connection.cursor() as cursor:
            try:
                cursor.execute(sql)
            except Exception:
                cursor.execute('ROLLBACK')
                raise
    finally:
        # A conexao volta ao pool: sem isto, testes seguintes herdariam autocommit
        # e perderiam transacoes/SAVEPOINT.
        raw.driver_connection.autocommit = False
        raw.close()


def structure(schema):
    inspector = inspect(engine)
    result = {}
    for table in sorted(inspector.get_table_names(schema=schema)):
        unique = {tuple(sorted(u['column_names'])) for u in inspector.get_unique_constraints(table, schema=schema)}
        indexes = inspector.get_indexes(table, schema=schema)
        unique |= {tuple(sorted(i['column_names'])) for i in indexes if i.get('unique')}
        result[table] = {
            'columns': {c['name']: (str(c['type']), c['nullable']) for c in inspector.get_columns(table, schema=schema)},
            'pk': tuple(inspector.get_pk_constraint(table, schema=schema)['constrained_columns']),
            'unique': sorted(unique),
            'indexes': sorted((i['name'], tuple(i['column_names'])) for i in indexes if not i.get('unique')),
            'fks': sorted((tuple(f['constrained_columns']), f['referred_table'], tuple(f['referred_columns']))
                          for f in inspector.get_foreign_keys(table, schema=schema)),
            'checks': sorted(c['name'] for c in inspector.get_check_constraints(table, schema=schema) if c.get('name')),
        }
    return result


@skipUnless(POSTGRES, 'Aplicacao das migrations exige o PostgreSQL descartavel')
class PostgresMigrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv('EDUFAST_TEST_DISPOSABLE') != '1':
            raise RuntimeError('Use the isolated runner; this suite rebuilds its test database')
        cls.migrations = load_migrations()

    def setUp(self):
        Base.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS {MODELO} CASCADE'))
        self.addCleanup(self.cleanup)
        created = {t for m in self.migrations for t in m['tables']}
        legacy = [t for t in Base.metadata.sorted_tables if t.name not in created]
        Base.metadata.create_all(engine, tables=legacy)
        with engine.begin() as connection:
            for migration in self.migrations:
                for table, column in migration['columns']:
                    connection.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))
            connection.execute(text("INSERT INTO usuarios (email, senha, tipo) VALUES "
                                    "('docente@example.test', 'hash', 'professor'), ('aluno@example.test', 'hash', 'aluno')"))

    def cleanup(self):
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS {MODELO} CASCADE'))
        Base.metadata.drop_all(engine)

    def apply(self, until=None):
        for migration in self.migrations:
            if until is not None and migration['versao'] > until:
                break
            run_sql((ESCOLA_DIR / migration['arquivo']).read_text(encoding='utf-8'))

    def test_sequential_migrations_reach_the_model_schema(self):
        self.apply()
        report = inventory(engine)
        self.assertEqual([i for i in report['migrations'] if i['situacao'] != APLICADA], [])
        self.assertEqual(report['versao_estrutural'], self.migrations[-1]['versao'])

        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA {MODELO}'))
        Base.metadata.create_all(engine.execution_options(schema_translate_map={None: MODELO}))
        migrated, expected = structure('public'), structure(MODELO)
        self.assertEqual(sorted(migrated), sorted(expected))
        for table in expected:
            with self.subTest(tabela=table):
                self.assertEqual(migrated[table], expected[table])

    def test_002_quarantines_existing_teachers_with_review_request(self):
        self.apply()
        with engine.connect() as connection:
            users = {r.email: r for r in connection.execute(text(
                'SELECT id, email, estado, auth_version, revisor_materiais FROM usuarios'))}
            requests = connection.execute(text(
                'SELECT solicitante_id, tipo, payload, estado, recurso_pendente FROM solicitacoes_alteracoes')).all()
        teacher, student = users['docente@example.test'], users['aluno@example.test']
        self.assertEqual((teacher.estado, teacher.auth_version, teacher.revisor_materiais), ('pendente', 1, False))
        self.assertEqual((student.estado, student.auth_version), ('ativo', 0))
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual((request.solicitante_id, request.tipo, request.estado, request.recurso_pendente),
                         (teacher.id, 'cadastro', 'pendente', f'cadastro:{teacher.id}'))
        self.assertEqual(json.loads(request.payload), {'usuario_id': teacher.id, 'papel_solicitado': 'professor'})

    def test_explicit_ids_advance_sequence_like_mysql_auto_increment(self):
        from app.database import get_session
        from app.models import UsuarioModel
        from app.models.curso_model import MigracaoSchemaModel
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with get_session() as db:
            db.add(UsuarioModel(id=10, email='Explicito@Example.test', senha='x', tipo='admin'))
            db.add(MigracaoSchemaModel(versao=3))  # sem sequencia: nada a ajustar
            db.commit()
            automatic = UsuarioModel(email='automatico@example.test', senha='x', tipo='admin')
            db.add(automatic)
            db.commit()
            self.assertEqual(automatic.id, 11)
            self.assertEqual(db.query(UsuarioModel).filter_by(id=10).one().email, 'explicito@example.test')
            # Nunca recua: valores ja entregues por outras sessoes continuam reservados.
            reserved = db.execute(text("SELECT setval(pg_get_serial_sequence('usuarios', 'id'), 50)")).scalar()
            self.assertEqual(reserved, 50)
            db.add(UsuarioModel(id=20, email='antigo@example.test', senha='x', tipo='admin'))
            db.commit()
            later = UsuarioModel(email='depois@example.test', senha='x', tipo='admin')
            db.add(later)
            db.commit()
            self.assertEqual(later.id, 51)

    def test_failed_migration_leaves_no_partial_state(self):
        self.apply(until=4)
        sql = (ESCOLA_DIR / '005_espaco_disciplina.sql').read_text(encoding='utf-8')
        broken = sql.replace('COMMIT;', 'SELECT 1 / 0;\nCOMMIT;')
        self.assertNotEqual(broken, sql)
        before = set(inspect(engine).get_table_names())
        with self.assertRaises(Exception):
            run_sql(broken)
        self.assertEqual(set(inspect(engine).get_table_names()), before)
        item = {i['versao']: i for i in inventory(engine)['migrations']}[5]
        self.assertEqual(item['situacao'], 'ausente')
        run_sql(sql)
        self.assertEqual({i['versao']: i for i in inventory(engine)['migrations']}[5]['situacao'], APLICADA)
