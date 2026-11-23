"""Verifica a infraestrutura e consistência dos casos, sem aprovar funcionalidades futuras."""
import ast
import json
from pathlib import Path
import unittest

from catalog import API, UNIT
from fixtures import ACTORS, REQUIRED, rows
from prepare_review import generated, TARGET


def validate():
    cases = API+UNIT
    identities = [case['id'] for case in cases]
    assert len(identities) == len(set(identities)), 'IDs de testes precisam ser únicos.'
    assert len(API) > 0 and len(UNIT) > 0
    for case in API:
        assert case['actor'] is None or case['actor'] in ACTORS, case['id']
        assert case['method'] in ('GET', 'POST', 'PATCH', 'DELETE'), case['id']
        assert case['path'].startswith('/'), case['id']
        assert not any(part in case for part in ('skip', 'xfail', 'expectedFailure')), case['id']
        for assertion in case.get('db', []):
            assert assertion['table'] in REQUIRED, case['id']
            assert set(assertion['where']).issubset(REQUIRED[assertion['table']]), case['id']
        if 'concurrent' in case:
            assert case['backends'] == ['postgresql'] and len(case['status']) == case['concurrent']
    for case in UNIT:
        assert ('result' in case)+('error' in case)+('different_from' in case) == 1, case['id']
        if 'error' in case:
            assert 400 <= case['status'] < 500
    data = rows('hash-test-only')
    for table, records in data.items():
        assert table in REQUIRED
        assert len({row['id'] for row in records}) == len(records), table
    for name, content in generated().items():
        assert (TARGET/name).read_text(encoding='utf-8') == content, f'Regenere a revisão: {name}'
    for path in Path(__file__).parent.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'))
    snapshots = Path(__file__).with_name('legacy')
    for backend in ('sqlite', 'mysql'):
        frozen = json.loads((snapshots/(backend+'.json')).read_text(encoding='utf-8'))
        assert len(frozen['statements']) >= 10
        assert frozen['source_commit'] == '1f034fae6df04c7d17af0e1054da694d3bfad799'
    print(f'Infraestrutura revisável: {len(API)} API, {len(UNIT)} unitários; documentos sincronizados.')


class InfrastructureTests(unittest.TestCase):
    def test_catalog_matches_review(self):
        validate()

    def test_destructive_guard_refuses_missing_flag(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from fixtures import assert_disposable
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(RuntimeError):
            assert_disposable(SimpleNamespace(url=None))

    def test_destructive_guard_refuses_unapproved_database(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from fixtures import assert_disposable
        url = SimpleNamespace(drivername='postgresql+psycopg', host='production.example.test', database='school', username='postgres')
        with patch.dict('os.environ', {'EDUFAST_TEST_NEXT': '1'}, clear=True), self.assertRaises(RuntimeError):
            assert_disposable(SimpleNamespace(url=url))

    def test_json_assertions_handle_nested_paths(self):
        from test_api import lookup
        self.assertEqual(lookup({'data': [{'id': 2}]}, 'data.0.id'), 2)
        with self.assertRaises(KeyError):
            lookup({'data': {}}, 'data.status')

    def test_all_contracts_are_discoverable(self):
        import os
        backend = os.environ.get('NEXT_BACKEND', 'sqlite')
        expected = len([case for case in API if backend in case.get('backends', ['sqlite', 'postgresql'])])
        self.assertEqual(unittest.defaultTestLoader.loadTestsFromName('test_api').countTestCases(), expected)
        self.assertEqual(unittest.defaultTestLoader.loadTestsFromName('test_unit').countTestCases(), len(UNIT))
        self.assertEqual(unittest.defaultTestLoader.loadTestsFromName('test_integration').countTestCases(), 10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
