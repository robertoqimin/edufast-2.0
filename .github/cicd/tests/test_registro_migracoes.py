"""A2: registro de versoes na inicializacao e sincronia das propostas geradas (SQLite descartavel)."""
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, text

from app import database
from app.database import Base
from app import models  # noqa: F401 — registra todas as tabelas da escola
from schema_inventory import ESCOLA_DIR, checksum_arquivo, inventory, load_migrations


class GeneratedProposalsTests(TestCase):
    def test_committed_proposals_match_the_generator(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('gerar_postgresql', ESCOLA_DIR / 'gerar_postgresql.py')
        gerador = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gerador)
        expected = gerador.gerados()
        self.assertIn('008_registro_migracoes.sql', expected)
        self.assertTrue(any(name.startswith('base/esquema_v') for name in expected))
        for name, content in expected.items():
            with self.subTest(arquivo=name):
                committed = (ESCOLA_DIR / name).read_bytes().replace(b'\r\n', b'\n').decode('utf-8')
                self.assertEqual(committed, content, 'Regenere com migrations/gerar_postgresql.py')

    def test_008_is_the_latest_proposal_and_registers_every_previous_one(self):
        migrations = load_migrations()
        self.assertEqual(migrations[-1]['arquivo'], '008_registro_migracoes.sql')
        sql = (ESCOLA_DIR / '008_registro_migracoes.sql').read_text(encoding='utf-8')
        for item in migrations[:-1]:
            with self.subTest(arquivo=item['arquivo']):
                self.assertIn(f"'{item['arquivo']}', 'detectada'", sql)


class StartupRegistryTests(TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)

    def insert(self, **values):
        columns = ', '.join(values)
        with self.engine.begin() as connection:
            connection.execute(text(f'INSERT INTO educafast_migracoes ({columns}) VALUES '
                                    f"({', '.join(':' + k for k in values)})"), values)

    def test_empty_and_known_registry_is_accepted(self):
        database.verificar_registro_migracoes(self.engine)
        self.insert(versao=8, arquivo='008_registro_migracoes.sql', origem='aplicada')
        database.verificar_registro_migracoes(self.engine)

    def test_registry_newer_than_code_is_refused(self):
        self.insert(versao=99, arquivo='099_futura.sql', origem='aplicada')
        with self.assertRaisesRegex(RuntimeError, 'mais nova que esta versao do codigo'):
            database.verificar_registro_migracoes(self.engine)

    def test_checksum_must_match_the_release_file(self):
        good = checksum_arquivo(ESCOLA_DIR / '004_frequencia.sql')
        self.insert(versao=4, arquivo='004_frequencia.sql', checksum=good, origem='aplicada')
        database.verificar_registro_migracoes(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE educafast_migracoes SET checksum = :c WHERE versao = 4"), {'c': 'f' * 64})
        with self.assertRaisesRegex(RuntimeError, 'conteudo diferente'):
            database.verificar_registro_migracoes(self.engine)
        self.assertTrue(any('conteudo diferente' in a for a in inventory(self.engine)['alertas']))

    def test_production_startup_accepts_registry_before_008(self):
        with self.engine.begin() as connection:
            connection.execute(text('DROP TABLE educafast_migracoes'))
            connection.execute(text('CREATE TABLE educafast_migracoes (versao INTEGER NOT NULL PRIMARY KEY)'))
            connection.execute(text('INSERT INTO educafast_migracoes (versao) VALUES (3)'))
        with patch.object(database, 'engine', self.engine), patch.object(database.Config, 'APP_ENV', 'production'):
            database.init_db()

    def test_production_startup_refuses_newer_registry(self):
        self.insert(versao=42, arquivo='042_futura.sql', origem='aplicada')
        with patch.object(database, 'engine', self.engine), patch.object(database.Config, 'APP_ENV', 'production'):
            with self.assertRaisesRegex(RuntimeError, 'migration 42'):
                database.init_db()
