"""A3: esquema base para banco vazio (SQLite descartavel; PostgreSQL em test_migrations_postgresql)."""
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text

from app import database
from app.database import Base
from app import models  # noqa: F401 — registra todas as tabelas da escola
from schema_base import arquivo_base, criar_esquema_base, linhas_registro_base, versao_base
from schema_inventory import APLICADA, ESCOLA_DIR, inventory, load_migrations


class BaseDefinitionTests(TestCase):
    def test_base_file_matches_latest_proposal(self):
        latest = load_migrations()[-1]['versao']
        self.assertEqual(versao_base(), latest)
        self.assertEqual(arquivo_base(), f'base/esquema_v{latest}.sql')
        self.assertTrue((ESCOLA_DIR / arquivo_base()).is_file())

    def test_older_base_files_are_kept_and_never_newer_than_latest(self):
        # Bancos criados por uma base antiga apontam para ela no registro: nao apagar.
        bases = sorted((ESCOLA_DIR / 'base').glob('esquema_v*.sql'))
        versions = [int(path.stem.removeprefix('esquema_v')) for path in bases]
        self.assertIn(versao_base(), versions)
        self.assertEqual(max(versions), versao_base())

    def test_registry_rows_cover_every_proposal_and_point_to_base(self):
        rows = linhas_registro_base()
        self.assertEqual([r['versao'] for r in rows], [m['versao'] for m in load_migrations()])
        self.assertEqual({r['arquivo'] for r in rows}, {arquivo_base()})
        self.assertEqual({r['origem'] for r in rows}, {'aplicada'})

    def test_base_sql_creates_every_model_table_and_registers_versions(self):
        sql = (ESCOLA_DIR / arquivo_base()).read_text(encoding='utf-8')
        for table in Base.metadata.sorted_tables:
            with self.subTest(tabela=table.name):
                self.assertIn(f'CREATE TABLE {table.name} (', sql)
        for row in linhas_registro_base():
            self.assertIn(f"({row['versao']}, '{row['descricao']}', '{row['arquivo']}', 'aplicada')", sql)
        self.assertTrue(sql.rstrip().endswith('COMMIT;'))


class SqliteBaseTests(TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.addCleanup(self.engine.dispose)

    def registry(self):
        with self.engine.connect() as connection:
            return [tuple(r) for r in connection.execute(text(
                'SELECT versao, arquivo, origem FROM educafast_migracoes ORDER BY versao'))]

    def test_empty_database_receives_complete_registered_schema(self):
        self.assertEqual(criar_esquema_base(self.engine), versao_base())
        self.assertEqual(set(inspect(self.engine).get_table_names()), set(Base.metadata.tables))
        self.assertEqual(self.registry(), [(r['versao'], r['arquivo'], 'aplicada') for r in linhas_registro_base()])
        report = inventory(self.engine)
        self.assertEqual([i for i in report['migrations'] if i['situacao'] != APLICADA], [])
        self.assertEqual(report['alertas'], [])
        database.verificar_registro_migracoes(self.engine)

    def test_database_with_any_table_is_refused_unchanged(self):
        with self.engine.begin() as connection:
            connection.execute(text('CREATE TABLE dados_existentes (id INTEGER PRIMARY KEY)'))
        with self.assertRaisesRegex(RuntimeError, 'banco vazio'):
            criar_esquema_base(self.engine)
        self.assertEqual(inspect(self.engine).get_table_names(), ['dados_existentes'])

    def test_production_startup_accepts_database_created_by_base(self):
        criar_esquema_base(self.engine)
        with patch.object(database, 'engine', self.engine), patch.object(database.Config, 'APP_ENV', 'production'):
            database.init_db()

    def test_school_fixture_resumes_after_base_without_school_data(self):
        from two_school_test_data import initialize
        from sqlalchemy.orm import Session
        criar_esquema_base(self.engine)  # tentativa interrompida: so esquema e registro
        initialize(self.engine, 'teste01')
        with Session(self.engine) as db:
            self.assertEqual(db.query(models.AlunoModel).count(), 20)
        self.assertEqual(len(self.registry()), versao_base())
