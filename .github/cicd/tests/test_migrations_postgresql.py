"""Aplica as propostas PostgreSQL sobre o esquema legado e o esquema base, em banco descartavel.

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
BASE = 'base_esperada'


def run_sql(sql, schema=None):
    """Mesmo executor usado pelo esquema base em producao (schema_base)."""
    from schema_base import executar_arquivo_postgresql
    executar_arquivo_postgresql(engine, sql, schema)


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
            for schema in (MODELO, BASE):
                connection.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
        self.addCleanup(self.cleanup)
        created = {t for m in self.migrations for t in m['tables']}
        legacy = [t for t in Base.metadata.sorted_tables if t.name not in created]
        Base.metadata.create_all(engine, tables=legacy)
        with engine.begin() as connection:
            legacy_names = {table.name for table in legacy}
            for migration in self.migrations:
                for table, column in migration['columns']:
                    if table in legacy_names:  # colunas de tabelas criadas por propostas vem com elas
                        connection.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))
            connection.execute(text("INSERT INTO usuarios (email, senha, tipo) VALUES "
                                    "('docente@example.test', 'hash', 'professor'), ('aluno@example.test', 'hash', 'aluno')"))

    def cleanup(self):
        with engine.begin() as connection:
            for schema in (MODELO, BASE):
                connection.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
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

    def test_base_schema_equals_legacy_plus_every_migration(self):
        from schema_base import arquivo_base, linhas_registro_base
        self.apply()
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA {BASE}'))
        run_sql((ESCOLA_DIR / arquivo_base()).read_text(encoding='utf-8'), schema=BASE)
        sequential, base = structure('public'), structure(BASE)
        self.assertEqual(sorted(sequential), sorted(base))
        for table in sequential:
            with self.subTest(tabela=table):
                self.assertEqual(base[table], sequential[table])
        with engine.connect() as connection:
            rows = [tuple(r) for r in connection.execute(text(
                f'SELECT versao, descricao, arquivo, origem FROM {BASE}.educafast_migracoes ORDER BY versao'))]
        self.assertEqual(rows, [(r['versao'], r['descricao'], r['arquivo'], r['origem']) for r in linhas_registro_base()])

    def test_base_creates_registered_database_accepted_in_production(self):
        from unittest.mock import patch
        from app import database
        from schema_base import criar_esquema_base, versao_base
        Base.metadata.drop_all(engine)
        self.assertEqual(criar_esquema_base(engine), versao_base())
        report = inventory(engine)
        self.assertEqual([i for i in report['migrations'] if i['situacao'] != APLICADA], [])
        self.assertEqual(report['alertas'], [])
        with patch.object(database.Config, 'APP_ENV', 'production'):
            database.init_db()
        with self.assertRaisesRegex(RuntimeError, 'banco vazio'):
            criar_esquema_base(engine)
        # A sessao seguinte nao herda search_path nem autocommit do arquivo executado.
        from app.database import get_session
        from app.models import UsuarioModel
        with get_session() as db:
            db.add(UsuarioModel(email='base@example.test', senha='x', tipo='admin'))
            db.commit()

    def registry(self):
        with engine.connect() as connection:
            return [tuple(row) for row in connection.execute(text(
                'SELECT versao, origem, arquivo FROM educafast_migracoes ORDER BY versao'))]

    def test_008_registers_every_complete_previous_migration(self):
        # A 008 cria o registro: detecta 001-007 e se marca aplicada. Propostas posteriores (009...)
        # sao registradas pelo aplicar_migracoes.py, coberto em test_aplicador_postgresql.
        self.apply(until=8)
        ate_008 = [m for m in self.migrations if m['versao'] <= 8]
        expected = [(m['versao'], 'detectada', m['arquivo']) for m in ate_008[:-1]]
        expected.append((8, 'aplicada', '008_registro_migracoes.sql'))
        self.assertEqual(self.registry(), expected)
        report = inventory(engine)
        self.assertEqual(report['alertas'], [])
        self.assertEqual(report['versoes_registradas'], [m['versao'] for m in ate_008])
        self.assertEqual(report['versao_estrutural'], 8)
        self.assertEqual({m['versao']: m['situacao'] for m in report['migrations']}[9], 'ausente')

    def test_008_skips_incomplete_structure_and_keeps_existing_rows(self):
        self.apply(until=7)
        with engine.begin() as connection:
            connection.execute(text('DROP TABLE estudo_secao_auditoria'))
            connection.execute(text('INSERT INTO educafast_migracoes (versao) VALUES (3)'))
        run_sql((ESCOLA_DIR / '008_registro_migracoes.sql').read_text(encoding='utf-8'))
        rows = {versao: (origem, arquivo) for versao, origem, arquivo in self.registry()}
        self.assertNotIn(6, rows)
        self.assertEqual(rows[3], ('aplicada', '003_restauracao_educafast.sql'))
        self.assertEqual(rows[5], ('detectada', '005_espaco_disciplina.sql'))
        self.assertEqual(rows[8], ('aplicada', '008_registro_migracoes.sql'))
        alerts = inventory(engine)['alertas']
        self.assertTrue(any('006_abas_disciplina.sql esta parcial' in a for a in alerts))

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
