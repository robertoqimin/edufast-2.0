"""Regras puras propostas: sem Flask, banco, rede ou implementação substituta."""
import copy
import importlib
import unittest
from catalog import UNIT


class PolicyTests(unittest.TestCase):
    pass


def make_test(case):
    def test(self):
        # Importação dentro do teste: a ausência do contrato é RED, nunca skip.
        policy = importlib.import_module('app.services.academic_policy')
        function = getattr(policy, case['function'])
        arguments = copy.deepcopy(case['arguments'])
        if 'error' in case:
            with self.assertRaises(policy.PolicyError) as caught:
                function(**arguments)
            self.assertEqual(caught.exception.code, case['error'])
            self.assertEqual(caught.exception.status, case['status'])
        else:
            result = function(**arguments)
            if 'different_from' in case:
                self.assertIsInstance(result, str)
                self.assertTrue(result)
                self.assertEqual(result, function(**copy.deepcopy(case['arguments'])))
                self.assertNotEqual(result, function(**copy.deepcopy(case['different_from'])))
            else:
                if isinstance(case['result'], bool):
                    self.assertIs(result, case['result'])
                else:
                    self.assertEqual(result, case['result'])
    test.__doc__ = case['title']
    return test


for case in UNIT:
    setattr(PolicyTests, 'test_'+case['id'].replace('-', '_'), make_test(case))
