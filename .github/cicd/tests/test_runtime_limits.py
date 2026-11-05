"""Contratos executados somente no banco descartável do runner de testes."""
import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from app import create_app
from runtime_limits import bounded_int


class RuntimeLimitsTests(unittest.TestCase):
    def test_default_limit_when_variable_is_absent(self):
        with patch.dict(os.environ):
            os.environ.pop('TEST_LIMIT', None)
            self.assertEqual(bounded_int('TEST_LIMIT', 4, 1, 32), 4)

    def test_limits_accept_inclusive_boundaries(self):
        for value in ('1', '32'):
            with self.subTest(value=value), patch.dict(os.environ, {'TEST_LIMIT': value}):
                self.assertEqual(bounded_int('TEST_LIMIT', 4, 1, 32), int(value))

    def test_invalid_limits_fail_closed(self):
        for value in ("0", "-1", "33", "9999", "invalid", "", "1.5"):
            with self.subTest(value=value), patch.dict(os.environ, {"TEST_LIMIT": value}):
                with self.assertRaises(ValueError):
                    bounded_int("TEST_LIMIT", 4, 1, 32)

    def test_database_saturation_returns_retryable_unavailable(self):
        app = create_app()
        app.config['TESTING'] = True
        isolated = create_engine('sqlite:///:memory:', poolclass=QueuePool,
                                 pool_size=1, max_overflow=0, pool_timeout=0.01)
        self.addCleanup(isolated.dispose)

        @app.get('/_test/pool-exhausted')
        def exhausted():
            with isolated.connect():
                return {'ok': True}

        with isolated.connect():
            response = app.test_client().get('/_test/pool-exhausted')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers['Retry-After'], '5')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertNotIn(b'QueuePool', response.data)
        self.assertEqual(app.test_client().get('/_test/pool-exhausted').status_code, 200)

    def test_request_limit_rejects_oversized_body_before_processing(self):
        app = create_app()
        app.config.update(TESTING=True, MAX_CONTENT_LENGTH=1024)
        processed_sizes = []

        @app.post('/_test/body')
        def body():
            from flask import request
            size = len(request.get_data())
            processed_sizes.append(size)
            return {'size': size}

        client = app.test_client()
        self.assertEqual(client.post('/_test/body', data=b'x' * 1024).status_code, 200)
        self.assertEqual(client.post('/_test/body', data=b'x' * 1025).status_code, 413)
        self.assertEqual(processed_sizes, [1024])
        self.assertEqual(client.post('/_test/body', data=b'x').json, {'size': 1})
