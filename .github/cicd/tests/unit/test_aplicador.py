"""Regras puras do aplicador (A4): formato transacional e literais do registro."""
import unittest

from schema_base import corpo_transacional, literal_registro, sql_checksum_base


class CorpoTransacionalTests(unittest.TestCase):
    def test_extracts_body_between_single_begin_and_final_commit(self):
        sql = '-- cabecalho\n\nBEGIN;\n\nCREATE TABLE a (id INT);\n\nCOMMIT;\n'
        self.assertEqual(corpo_transacional(sql).strip(), 'CREATE TABLE a (id INT);')

    def test_accepts_windows_line_endings(self):
        self.assertIn('SELECT 1;', corpo_transacional('BEGIN;\r\nSELECT 1;\r\nCOMMIT;\r\n'))

    def test_refuses_files_outside_reviewed_format(self):
        for sql in ['CREATE TABLE a (id INT);',               # sem transacao
                    'BEGIN;\nSELECT 1;\n',                     # sem COMMIT
                    'SELECT 0;\nBEGIN;\nSELECT 1;\nCOMMIT;',   # comando antes do BEGIN
                    'BEGIN;\nSELECT 1;\nCOMMIT;\nSELECT 2;',   # comando depois do COMMIT
                    'BEGIN;\nBEGIN;\nSELECT 1;\nCOMMIT;']:     # BEGIN duplicado
            with self.subTest(sql=sql), self.assertRaises(RuntimeError):
                corpo_transacional(sql)


class LiteralRegistroTests(unittest.TestCase):
    def test_valid_values(self):
        self.assertEqual(literal_registro(8, 'versao'), '8')
        self.assertEqual(literal_registro('base/esquema_v8.sql', 'arquivo'), "'base/esquema_v8.sql'")
        self.assertEqual(literal_registro('a' * 64, 'checksum'), "'" + 'a' * 64 + "'")

    def test_refuses_anything_that_could_escape_the_literal(self):
        for valor, tipo in [("x'; DROP TABLE usuarios; --.sql", 'arquivo'), ('../segredo.sql', 'arquivo'),
                            ('A' * 64, 'checksum'), ('abc', 'checksum'), ("nome'", 'descricao'), ('dois', 'versao')]:
            with self.subTest(valor=valor), self.assertRaises((RuntimeError, ValueError)):
                literal_registro(valor, tipo)

    def test_checksum_update_targets_only_the_base_rows(self):
        sql = sql_checksum_base('base/esquema_v8.sql', 'b' * 64)
        self.assertIn("WHERE arquivo = 'base/esquema_v8.sql'", sql)


if __name__ == '__main__':
    unittest.main()
