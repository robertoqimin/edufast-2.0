"""O portão de comparação precisa detectar perdas reais, mesmo com totais iguais."""
import json
from pathlib import Path
import tempfile
import unittest
from comparar_resultados import comparar


class ComparacaoCITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old, self.new = self.root / 'old', self.root / 'new'
        for folder in (self.old, self.new):
            folder.mkdir()
            for nome, contagens in (('postman', {'requisicoes': 1, 'verificacoes': 1}),
                                    ('regressao', {'testes': 1, 'ignorados': 0})):
                (folder / f'{nome}-resumo.json').write_text(json.dumps({**contagens, 'aprovado': True,
                    'falhas': 0, 'erros': 0, 'duracao_segundos': 1}), encoding='utf-8')
            (folder / 'postman-junit.xml').write_text('<testsuites><testsuite name="Login"><testcase name="HTTP 200"/></testsuite></testsuites>', encoding='utf-8')
            (folder / 'regressao-unittest.txt').write_text('test_login (test_auth.Auth.test_login) ... ok\n', encoding='utf-8')

    def test_unchanged_coverage_passes(self):
        self.assertTrue(comparar(self.old, self.new)['aprovado'])

    def test_replaced_assertion_fails_even_if_summary_counts_match(self):
        (self.new / 'postman-junit.xml').write_text('<testsuites><testsuite name="Outra rota"><testcase name="HTTP 200"/></testsuite></testsuites>', encoding='utf-8')
        result = comparar(self.old, self.new)
        self.assertFalse(result['aprovado'])
        self.assertIn('Login / HTTP 200', result['api_removidos'])

    def test_failure_in_xml_cannot_be_hidden_by_success_summary(self):
        (self.new / 'postman-junit.xml').write_text('<testsuites><testsuite name="Login"><testcase name="HTTP 200"><failure>Regressão</failure></testcase></testsuite></testsuites>', encoding='utf-8')
        self.assertFalse(comparar(self.old, self.new)['aprovado'])
