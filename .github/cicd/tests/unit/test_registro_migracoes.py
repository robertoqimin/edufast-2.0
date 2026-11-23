"""Regras do registro de migrations (A2), sem banco nem Flask."""
import tempfile
import unittest
from pathlib import Path

from schema_inventory import checksum_arquivo, problemas_registro

MIGRATIONS = [{'versao': 1, 'arquivo': '001_a.sql'}, {'versao': 2, 'arquivo': '002_b.sql'}]


class RegistroTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.dir = Path(self.folder.name)
        (self.dir / '001_a.sql').write_bytes(b'BEGIN;\nSELECT 1;\nCOMMIT;\n')

    def test_known_versions_without_checksum_are_accepted(self):
        rows = [{'versao': 1, 'arquivo': '001_a.sql', 'checksum': None}, {'versao': 2}]
        self.assertEqual(problemas_registro(rows, MIGRATIONS, self.dir), [])

    def test_newer_database_than_code_is_refused(self):
        problems = problemas_registro([{'versao': 3}], MIGRATIONS, self.dir)
        self.assertEqual(len(problems), 1)
        self.assertIn('migration 3', problems[0])
        self.assertIn('ultima conhecida: 2', problems[0])

    def test_matching_checksum_is_accepted_and_ignores_line_endings(self):
        digest = checksum_arquivo(self.dir / '001_a.sql')
        (self.dir / '001_a.sql').write_bytes(b'BEGIN;\r\nSELECT 1;\r\nCOMMIT;\r\n')
        self.assertEqual(checksum_arquivo(self.dir / '001_a.sql'), digest)
        rows = [{'versao': 1, 'arquivo': '001_a.sql', 'checksum': digest}]
        self.assertEqual(problemas_registro(rows, MIGRATIONS, self.dir), [])

    def test_changed_file_is_refused(self):
        rows = [{'versao': 1, 'arquivo': '001_a.sql', 'checksum': '0' * 64}]
        problems = problemas_registro(rows, MIGRATIONS, self.dir)
        self.assertEqual(len(problems), 1)
        self.assertIn('conteudo diferente', problems[0])

    def test_missing_registered_file_is_refused(self):
        rows = [{'versao': 2, 'arquivo': '002_b.sql', 'checksum': 'a' * 64}]
        self.assertIn('nao existe', problemas_registro(rows, MIGRATIONS, self.dir)[0])


if __name__ == '__main__':
    unittest.main()
