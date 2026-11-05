"""Configuração de limites sem Flask, SQLAlchemy, banco ou Docker."""
import os
import unittest
from unittest.mock import patch

from runtime_limits import bounded_int


class RuntimeConfigTests(unittest.TestCase):
    def test_default_limit_when_variable_is_absent(self):
        with patch.dict(os.environ):
            os.environ.pop('TEST_LIMIT', None)
            self.assertEqual(bounded_int('TEST_LIMIT', 4, 1, 32), 4)

    def test_limits_accept_inclusive_boundaries(self):
        for value in ('1', '32'):
            with self.subTest(value=value), patch.dict(os.environ, {'TEST_LIMIT': value}):
                self.assertEqual(bounded_int('TEST_LIMIT', 4, 1, 32), int(value))

    def test_invalid_limits_fail_closed(self):
        for value in ('0', '-1', '33', '9999', 'invalid', '', '1.5'):
            with self.subTest(value=value), patch.dict(os.environ, {'TEST_LIMIT': value}):
                with self.assertRaises(ValueError):
                    bounded_int('TEST_LIMIT', 4, 1, 32)
