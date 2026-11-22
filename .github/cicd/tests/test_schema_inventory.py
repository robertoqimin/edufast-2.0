"""Inventario de migrations contra bancos reais descartaveis, sempre somente leitura."""
import os
from unittest import TestCase, skipUnless

from sqlalchemy import create_engine, inspect, text

from app.database import Base, engine as app_engine
from app import models  # noqa: F401 — registra todas as tabelas da escola
from schema_inventory import APLICADA, AUSENTE, PARCIAL, inventory, load_migrations

MYSQL = app_engine.dialect.name == 'mysql'


def table_count(engine):
    return len(inspect(engine).get_table_names())


class SqliteInventoryTests(TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.addCleanup(self.engine.dispose)
        self.latest = load_migrations()[-1]['versao']

    def by_version(self, report):
        return {item['versao']: item for item in report['migrations']}

    def test_empty_database_has_every_migration_absent(self):
        report = inventory(self.engine)
        self.assertTrue(all(item['situacao'] == AUSENTE for item in report['migrations']))
        self.assertEqual(report['versao_estrutural'], 0)
        self.assertNotIn('versoes_registradas', report)

    def test_current_models_match_every_proposed_migration(self):
        Base.metadata.create_all(self.engine)
        report = inventory(self.engine)
        not_applied = [item for item in report['migrations'] if item['situacao'] != APLICADA]
        self.assertEqual(not_applied, [])
        self.assertEqual(report['versao_estrutural'], self.latest)

    def test_missing_table_marks_only_its_migration_as_partial(self):
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text('DROP TABLE frequencia_presencas'))
        items = self.by_version(inventory(self.engine))
        self.assertEqual(items[4]['situacao'], PARCIAL)
        self.assertEqual(items[4]['faltando'], ['tabela frequencia_presencas'])
        self.assertEqual(items[3]['situacao'], APLICADA)
        self.assertEqual(items[5]['situacao'], APLICADA)

    def test_registered_versions_are_reported_without_writing(self):
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text('INSERT INTO educafast_migracoes (versao) VALUES (3)'))
        before = table_count(self.engine)
        report = inventory(self.engine)
        self.assertEqual(report['versoes_registradas'], [3])
        self.assertTrue(any('educafast_migracoes' in alert for alert in report['alertas']))
        self.assertEqual(table_count(self.engine), before)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM educafast_migracoes')).scalar_one(), 1)


@skipUnless(MYSQL, 'Inventario MySQL requer o runner descartavel')
class MysqlInventoryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv('EDUFAST_TEST_DISPOSABLE') != '1':
            raise RuntimeError('Use the isolated runner; this suite rebuilds its test database')

    def setUp(self):
        Base.metadata.drop_all(app_engine)
        Base.metadata.create_all(app_engine)

    def test_mysql_reflection_matches_every_proposed_migration(self):
        report = inventory(app_engine)
        not_applied = [item for item in report['migrations'] if item['situacao'] != APLICADA]
        self.assertEqual(not_applied, [])
        self.assertEqual(report['versao_estrutural'], load_migrations()[-1]['versao'])

    def test_mysql_not_null_video_is_detected_as_pending_007(self):
        with app_engine.begin() as connection:
            connection.execute(text('DELETE FROM curso_aulas'))
            connection.execute(text('ALTER TABLE curso_aulas MODIFY COLUMN video_id VARCHAR(11) NOT NULL'))
        item = {i['versao']: i for i in inventory(app_engine)['migrations']}[7]
        self.assertEqual(item['situacao'], PARCIAL)
        self.assertEqual(item['faltando'], ['coluna curso_aulas.video_id aceita nulo'])
