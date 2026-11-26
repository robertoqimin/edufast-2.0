"""A2: registro de versoes na inicializacao e sincronia das propostas geradas (SQLite descartavel)."""
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, text

from app import database
from app.database import Base
from app import models  # noqa: F401 — registra todas as tabelas da escola
from schema_inventory import ESCOLA_DIR, checksum_arquivo, inventory, load_migrations


class GeneratedProposalsTests(TestCase):
    def test_frozen_files_match_the_checksum_manifest(self):
        """Propostas e bases aplicadas nao podem mudar: o checksum gravado nos bancos as recusaria."""
        import json
        manifest = json.loads((ESCOLA_DIR / 'checksums.json').read_text(encoding='utf-8'))
        files = sorted([p.name for p in ESCOLA_DIR.glob('[0-9][0-9][0-9]_*.sql')] +
                       ['base/' + p.name for p in (ESCOLA_DIR / 'base').glob('esquema_v*.sql')])
        self.assertEqual(sorted(manifest), files, 'Todo arquivo novo entra no manifesto pelo gerador')
        for name, digest in manifest.items():
            with self.subTest(arquivo=name):
                self.assertEqual(checksum_arquivo(ESCOLA_DIR / name), digest, 'Arquivo congelado foi alterado')

    def test_latest_base_matches_current_models(self):
        """Modelo alterado sem nova proposta/base aparece aqui antes de chegar a um banco."""
        import importlib.util
        spec = importlib.util.spec_from_file_location('gerar_postgresql', ESCOLA_DIR / 'gerar_postgresql.py')
        gerador = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gerador)
        name, content = gerador.gerar_base()
        committed = (ESCOLA_DIR / name).read_bytes().replace(b'\r\n', b'\n').decode('utf-8')
        self.assertEqual(committed, content, 'Modelos mudaram: crie nova proposta e nova base, sem editar as antigas')

    def test_008_registers_every_previous_one_and_010_is_the_latest(self):
        migrations = load_migrations()
        self.assertEqual(migrations[-1]['arquivo'], '010_unidades.sql')
        sql = (ESCOLA_DIR / '008_registro_migracoes.sql').read_text(encoding='utf-8')
        for item in [m for m in migrations if m['versao'] < 8]:
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
