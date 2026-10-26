"""API real via cliente Flask, fixtures reais no banco; sem simular respostas."""
from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
import hmac
import io
import json
import os
import re
import threading
import unittest

from catalog import API
from fixtures import ACTORS, PASSWORD, assert_disposable, schema, seed


def lookup(value, dotted):
    for part in dotted.split('.'):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import create_app
        from app.database import engine
        from werkzeug.security import generate_password_hash
        assert_disposable(engine)
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.engine = engine
        cls.metadata = schema(engine)
        cls.password_hash = generate_password_hash(PASSWORD)

    def setUp(self):
        seed(self.engine, self.metadata, self.app.config['UPLOAD_FOLDER'], self.password_hash)
        self.client = self.app.test_client()

    def authenticate(self, actor):
        if not actor:
            return {}
        response = self.client.post('/api/v1/auth/login', json={'email': actor+'@example.test', 'senha': PASSWORD})
        self.assertEqual(response.status_code, 200, 'Login do contrato ainda não implementado: '+response.get_data(as_text=True)[:300])
        token = lookup(response.get_json(), 'data.access_token')
        self.assertIsInstance(token, str)
        headers = {'Authorization': 'Bearer '+token}
        if actor not in ('plataforma', 'sem_vinculo', 'convidado'):
            school = 2 if actor in ('gestor_b', 'aluno_b') else 1
            selected = self.client.post('/api/v1/contexto', json={'escola_id': school}, headers=headers)
            self.assertEqual(selected.status_code, 200, 'Contexto inicial precisa ser selecionável.')
        return headers

    def send(self, client, case, headers):
        kwargs = {'method': case['method'], 'headers': headers}
        if 'upload' in case:
            upload = case['upload']
            content = b'x'*upload['size'] if 'size' in upload else upload['content'].encode()
            kwargs['data'] = {'arquivo': (io.BytesIO(content), upload['filename'], upload['content_type'])}
        elif 'json' in case:
            kwargs['json'] = case['json']
        return client.open(case['path'], **kwargs)

    def assert_database(self, checks):
        from sqlalchemy import select, func
        with self.engine.connect() as connection:
            for check in checks:
                table = self.metadata.tables[check['table']]
                clauses = [table.c[key] == value for key, value in check['where'].items()]
                count = connection.scalar(select(func.count()).select_from(table).where(*clauses))
                self.assertEqual(count, check['count'], str(check))

    def scenario(self, case):
        headers = self.authenticate(case['actor'])
        if case.get('auth_override') == 'tampered':
            headers = {'Authorization': headers['Authorization']+'tampered'}
        if case.get('auth_override') == 'expired':
            # Usa o token emitido de verdade, preserva claims e altera somente exp.
            token = headers['Authorization'].split(' ', 1)[1]
            first, middle, _ = token.split('.')
            decode = lambda value: base64.urlsafe_b64decode(value+'='*((4-len(value)%4)%4))
            encode = lambda value: base64.urlsafe_b64encode(value).rstrip(b'=').decode()
            self.assertEqual(json.loads(decode(first))['alg'], 'HS256')
            payload = json.loads(decode(middle))
            payload['exp'] = 1
            middle = encode(json.dumps(payload, separators=(',', ':')).encode())
            message = first+'.'+middle
            signature = encode(hmac.new(self.app.config['SECRET_KEY'].encode(), message.encode(), hashlib.sha256).digest())
            headers = {'Authorization': 'Bearer '+message+'.'+signature}
        for before in case.get('before', []):
            response = self.send(self.client, before, headers)
            self.assertEqual(response.status_code, before['status'])
        if 'mutate' in case:
            mutation = case['mutate']
            table = self.metadata.tables[mutation['table']]
            clauses = [table.c[key] == value for key, value in mutation['where'].items()]
            with self.engine.begin() as connection:
                result = connection.execute(table.update().where(*clauses).values(**mutation['values']))
                self.assertEqual(result.rowcount, 1)
        if case.get('concurrent'):
            barrier = threading.Barrier(case['concurrent'])

            def concurrent_request(_):
                with self.app.test_client() as client:
                    barrier.wait(timeout=10)
                    return self.send(client, case, headers)

            with ThreadPoolExecutor(max_workers=case['concurrent']) as executor:
                responses = list(executor.map(concurrent_request, range(case['concurrent'])))
            self.assertEqual(sorted(r.status_code for r in responses), sorted(case['status']))
            for response in responses:
                if response.status_code == 409:
                    self.assertEqual(lookup(response.get_json(), 'error.code'), case['conflict_error'])
        else:
            response = self.send(self.client, case, headers)
            self.assertEqual(response.status_code, case['status'], response.get_data(as_text=True)[:500])
            body = response.get_data(as_text=True)
            if 'error' in case:
                self.assertTrue(response.is_json, 'Erro da API deve ser JSON.')
                self.assertEqual(lookup(response.get_json(), 'error.code'), case['error'])
            for dotted, expected in case.get('equals', {}).items():
                self.assertEqual(lookup(response.get_json(), dotted), expected)
            if 'ids' in case:
                self.assertEqual([item['id'] for item in response.get_json()['data']], case['ids'])
            for marker in case.get('absent', []):
                self.assertNotIn(marker, body)
            if 'body_contains' in case:
                self.assertIn(case['body_contains'], body)
            for name, fragment in case.get('headers_contains', {}).items():
                self.assertIn(fragment, response.headers.get(name, ''))
            if 'followup' in case:
                next_request = dict(case['followup'])
                next_request['path'] = re.sub(r'\{([a-zA-Z0-9_.]+)\}', lambda match: str(lookup(response.get_json(), match.group(1))), next_request['path'])
                followup = self.send(self.client, next_request, headers)
                self.assertEqual(followup.status_code, next_request['status'])
                self.assertIn(next_request['body_contains'], followup.get_data(as_text=True))
        self.assert_database(case.get('db', []))


def make_test(case):
    def test(self):
        self.scenario(case)
    test.__doc__ = case['title']
    return test


BACKEND = os.environ.get('NEXT_BACKEND', 'sqlite')
for case in API:
    if BACKEND in case.get('backends', ['sqlite', 'mysql']):
        setattr(ApiTests, 'test_'+case['id'].replace('-', '_'), make_test(case))
