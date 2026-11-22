"""Leitura das migrations e classificacao do inventario, sem banco nem Flask."""
import unittest

from schema_inventory import (APLICADA, AUSENTE, CENTRAL_DIR, PARCIAL, classify,
                              load_migrations, parse_migration)


def migration(versao, **parts):
    base = {'tables': [], 'columns': [], 'indexes': [], 'nullable': []}
    return {'versao': versao, 'arquivo': f'{versao:03d}_teste.sql', **base, **parts}


def table(*columns, indexes=(), nullable=()):
    return {'columns': {c: c in nullable for c in columns}, 'indexes': set(indexes)}


class ParseMigrationTests(unittest.TestCase):
    def test_extracts_tables_columns_indexes_and_nullability(self):
        parsed = parse_migration("""
            -- CREATE TABLE comentario_ignorado (id INT);
            ALTER TABLE usuarios
                ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'ativo',
                ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0;
            CREATE TABLE solicitacoes (id INTEGER NOT NULL, PRIMARY KEY (id));
            CREATE INDEX ix_solicitacoes_id ON solicitacoes (id);
            ALTER TABLE curso_aulas MODIFY COLUMN video_id VARCHAR(11) NULL;
            ALTER TABLE outra MODIFY COLUMN nome VARCHAR(10) NOT NULL;
        """)
        self.assertEqual(parsed['tables'], ['solicitacoes'])
        self.assertEqual(parsed['columns'], [('usuarios', 'estado'), ('usuarios', 'auth_version')])
        self.assertEqual(parsed['indexes'], [('solicitacoes', 'ix_solicitacoes_id')])
        self.assertEqual(parsed['nullable'], [('curso_aulas', 'video_id')])

    def test_repository_migrations_are_ordered_and_detectable(self):
        found = load_migrations()
        self.assertEqual([m['versao'] for m in found], list(range(1, len(found) + 1)))
        self.assertGreaterEqual(len(found), 7)
        for item in found:
            with self.subTest(arquivo=item['arquivo']):
                self.assertTrue(item['tables'] or item['columns'] or item['nullable'])
        by_version = {m['versao']: m for m in found}
        self.assertIn(('usuarios', 'auth_version'), by_version[2]['columns'])
        self.assertIn('frequencia_chamadas', by_version[4]['tables'])
        self.assertIn(('curso_aulas', 'video_id'), by_version[7]['nullable'])

    def test_central_migration_is_read_separately(self):
        central = load_migrations(CENTRAL_DIR)
        self.assertEqual(central[0]['versao'], 1)
        self.assertIn('platform_owner', central[0]['tables'])


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.migrations = [
            migration(1, columns=[('alunos', 'versao')]),
            migration(2, tables=['a', 'b'], indexes=[('a', 'ix_a')]),
            migration(3, nullable=[('aulas', 'video_id')]),
        ]

    def situations(self, report):
        return [item['situacao'] for item in report['migrations']]

    def test_empty_structure_is_absent(self):
        report = classify(self.migrations, {'tables': {}})
        self.assertEqual(self.situations(report), [AUSENTE] * 3)
        self.assertEqual(report['versao_estrutural'], 0)
        self.assertEqual(report['alertas'], [])
        self.assertTrue(report['somente_leitura'])

    def test_complete_structure_is_applied(self):
        snap = {'tables': {'alunos': table('id', 'versao'), 'a': table('id', indexes=['ix_a']),
                           'b': table('id'), 'aulas': table('id', 'video_id', nullable=['video_id'])}}
        report = classify(self.migrations, snap)
        self.assertEqual(self.situations(report), [APLICADA] * 3)
        self.assertEqual(report['versao_estrutural'], 3)

    def test_partial_lists_what_is_missing(self):
        snap = {'tables': {'alunos': table('id', 'versao'), 'a': table('id')}}
        report = classify(self.migrations, snap)
        self.assertEqual(self.situations(report), [APLICADA, PARCIAL, AUSENTE])
        self.assertEqual(report['migrations'][1]['faltando'], ['tabela b', 'indice a.ix_a'])
        self.assertEqual(report['versao_estrutural'], 1)
        self.assertTrue(any('parcial' in alert for alert in report['alertas']))

    def test_not_null_column_does_not_satisfy_nullable_change(self):
        snap = {'tables': {'aulas': table('id', 'video_id')}}
        self.assertEqual(classify(self.migrations, snap)['migrations'][2]['situacao'], AUSENTE)

    def test_out_of_order_application_is_reported(self):
        snap = {'tables': {'a': table('id', indexes=['ix_a']), 'b': table('id')}}
        report = classify(self.migrations, snap)
        self.assertEqual(report['versao_estrutural'], 0)
        self.assertTrue(any('002_teste.sql' in alert and 'anterior' in alert for alert in report['alertas']))

    def test_registry_divergence_is_reported(self):
        snap = {'tables': {'alunos': table('id', 'versao')}}
        report = classify(self.migrations, snap, registered=[1, 3])
        self.assertEqual(report['versoes_registradas'], [1, 3])
        self.assertTrue(any('versoes 3' in alert for alert in report['alertas']))
        matching = classify(self.migrations, snap, registered=[1])
        self.assertFalse(any('educafast_migracoes' in alert for alert in matching['alertas']))


if __name__ == '__main__':
    unittest.main()
