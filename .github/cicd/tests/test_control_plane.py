"""Contratos do painel central, exclusivamente em banco descartavel."""
import hashlib
import json
import os
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url
import control_plane
from control_plane import create_app, utcnow, today
from control_plane.models import Base, Owner, School, Person, Movement, Audit
from control_plane.schema import proposed_sql


@unittest.skipUnless(os.getenv('EDUFAST_TEST_DISPOSABLE') == '1', 'Exige opt-in de banco descartavel')
class PlatformTest(unittest.TestCase):
    def setUp(self):
        target = os.getenv('PLATFORM_TEST_DATABASE_URL', 'sqlite:///:memory:')
        parsed = make_url(target)
        if target != 'sqlite:///:memory:' and not (parsed.get_backend_name() == 'postgresql' and parsed.host == 'db-platform-test' and parsed.database == 'edufast_platform_disposable'):
            raise RuntimeError('Permitido somente banco central descartavel do executor.')
        self.app = create_app(dict(TESTING=True, DATABASE_URL=target,
            SECRET_KEY='central-only-synthetic-secret-' + 'x' * 32,
            PLATFORM_ENV='development', SESSION_COOKIE_SECURE=False))
        self.engine = self.app.extensions['platform_engine']
        Base.metadata.create_all(self.engine)
        self.runner = self.app.test_cli_runner()
        result = self.runner.invoke(args=['create-owner', '--email', 'owner@example.test'],
                                    input='Owner-test-password-2026!\nOwner-test-password-2026!\n')
        self.assertEqual(result.exit_code, 0, result.output)
        self.client = self.app.test_client()
        self.client.get('/login')
        self.post('/login', dict(email='owner@example.test', password='Owner-test-password-2026!'))

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def post(self, url, data, client=None, csrf=True):
        client = client or self.client
        with client.session_transaction() as cookie:
            token = cookie.get('csrf_token', '')
        return client.post(url, json=data, headers={'X-CSRF-Token': token} if csrf else {})

    def school(self, slug='teste01'):
        result = self.post('/escolas', dict(name='Escola ' + slug, slug=slug,
            domain=slug + '.example.test', monthly='500,00'))
        self.assertEqual(result.status_code, 200, result.json)
        return result.json['id']

    def payload(self, count=2):
        return dict(captured_at=utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'), people=[dict(
            local_id=i, name='Aluno ' + str(i), email=f'aluno{i}@example.test', role='aluno', state='ativo') for i in range(1, count+1)])

    def integrate(self, slug, payload, token='school-one-token'):
        return self.client.post('/integracao/' + slug + '/pessoas', json=payload,
                                headers={'Authorization': 'Bearer ' + token})

    def key(self, sid, token='school-one-token'):
        with Session(self.engine) as db:
            db.get(School, sid).token_hash = hashlib.sha256(token.encode()).hexdigest()
            db.commit()

    def entry(self, sid, kind='receita', amount='500,00', **overrides):
        data = dict(kind=kind, amount=amount, day=today().isoformat(),
                    description='Pagamento sintetico', request_key=str(uuid4()))
        data.update(overrides)
        return self.post(f'/escolas/{sid}/movimentos', data), data

    def test_no_school_session_or_bearer_can_access_owner(self):
        client = self.app.test_client()
        for role in ['admin', 'super_admin', 'professor', 'aluno']:
            with client.session_transaction() as cookie:
                cookie.update(user_id=1, user_role=role, auth_version=0)
            self.assertEqual(client.get('/?formato=json').status_code, 401)
        self.assertEqual(self.client.get('/?formato=json', headers={'Authorization': 'Bearer school-token'}).status_code, 401)
        self.assertEqual(client.get('/pessoas').status_code, 302)

    def test_login_csrf_lockout_and_password_reset_revokes_sessions(self):
        client = self.app.test_client()
        client.get('/login')
        self.assertEqual(self.post('/login', {}, client, csrf=False).status_code, 403)
        for _ in range(5):
            self.assertEqual(self.post('/login', dict(email='owner@example.test', password='wrong'), client).status_code, 401)
        self.assertEqual(self.post('/login', dict(email='owner@example.test', password='Owner-test-password-2026!'), client).status_code, 429)
        result = self.runner.invoke(args=['reset-owner-password'], input='New-test-password-2026!\nNew-test-password-2026!\n')
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(self.client.get('/?formato=json').status_code, 401)
        self.assertEqual(self.post('/login', dict(email='owner@example.test', password='New-test-password-2026!'), client).status_code, 200)

    def test_single_owner_and_secret_headers(self):
        self.assertNotEqual(self.runner.invoke(args=['create-owner'], input='other@example.test\nAnother-password-2026!\nAnother-password-2026!\n').exit_code, 0)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        with Session(self.engine) as db:
            self.assertNotIn('Owner-test-password-2026!', db.get(Owner, 1).password_hash)

    def test_browser_form_survives_favicon_and_other_anonymous_requests(self):
        client = self.app.test_client()
        client.get('/login')
        with client.session_transaction() as cookie:
            token = cookie['csrf_token']
        self.assertEqual(client.get('/favicon.ico').status_code, 404)
        self.assertEqual(client.get('/pessoas').status_code, 302)
        response = client.post('/login', data=dict(email='owner@example.test', password='Owner-test-password-2026!', csrf_token=token))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(client.get('/').status_code, 200)

    def test_school_validation_duplicates_and_csrf(self):
        sid = self.school()
        self.assertEqual(self.post('/escolas', dict(name='Duplicada', slug='teste01', domain='outro.example.test')).status_code, 409)
        self.assertEqual(self.post('/escolas', dict(name='Invalida', slug='../outro', domain='a.example.test')).status_code, 400)
        self.assertEqual(self.post('/escolas', {}, csrf=False).status_code, 403)
        self.assertEqual(self.post('/escolas', []).status_code, 400)
        self.assertEqual(self.client.get('/escolas/' + str(sid)).status_code, 200)
        self.assertEqual(self.post(f'/escolas/{sid}', dict(name='Escola', version=1, monthly='500', state=[])).status_code, 400)

    def test_school_version_conflict_does_not_overwrite(self):
        sid = self.school()
        body = dict(name='Novo nome', monthly='600,10', state='ativa', version=1)
        self.assertEqual(self.post(f'/escolas/{sid}', body).status_code, 200)
        self.assertEqual(self.post(f'/escolas/{sid}', body).status_code, 409)
        row = self.client.get('/?formato=json').json['schools'][0]
        self.assertEqual(row['monthly_cents'], 60010)
        self.assertEqual(row['state'], 'ativa')

    def test_integration_scoped_to_school_and_replaces_only_own_people(self):
        one, two = self.school(), self.school('teste02')
        self.key(one)
        self.key(two, 'school-two-token')
        self.assertEqual(self.integrate('teste01', self.payload()).status_code, 200)
        self.assertEqual(self.integrate('teste02', self.payload(), 'school-two-token').status_code, 200)
        self.assertEqual(self.integrate('teste02', self.payload()).status_code, 401)
        self.assertEqual(self.integrate('teste01', self.payload(1)).status_code, 200)
        response = self.client.get('/pessoas?formato=json').json
        self.assertEqual(response['total'], 3)
        self.assertEqual({p['school_id'] for p in response['people']}, {one, two})
        self.assertEqual(self.client.get(f'/pessoas?formato=json&escola={two}').json['total'], 2)

    def test_invalid_snapshot_preserves_last_directory_and_replay_rejected(self):
        sid = self.school()
        self.key(sid)
        payload = self.payload()
        self.assertEqual(self.integrate('teste01', payload).status_code, 200)
        self.assertEqual(self.integrate('teste01', payload).status_code, 409)
        invalid = self.payload()
        invalid['people'][1]['local_id'] = 1
        self.assertEqual(self.integrate('teste01', invalid).status_code, 400)
        invalid = self.payload()
        invalid['people'][0]['password'] = 'must-not-be-collected'
        self.assertEqual(self.integrate('teste01', invalid).status_code, 400)
        invalid = self.payload()
        invalid['people'][0]['role'] = []
        self.assertEqual(self.integrate('teste01', invalid).status_code, 400)
        invalid = self.payload()
        invalid['captured_at'] = (utcnow() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        self.assertEqual(self.integrate('teste01', invalid).status_code, 409)
        self.assertEqual(self.client.get('/pessoas?formato=json').json['total'], 2)

    def test_suspension_blocks_integration_without_school_cookie_fallback(self):
        sid = self.school()
        self.key(sid)
        self.assertEqual(self.client.post('/integracao/teste01/pessoas', json=self.payload()).status_code, 401)
        with Session(self.engine) as db:
            db.get(School, sid).state = 'suspensa'
            db.commit()
        self.assertEqual(self.integrate('teste01', self.payload()).status_code, 403)

    def test_people_pagination_search_and_audit(self):
        sid = self.school()
        self.key(sid)
        self.assertEqual(self.integrate('teste01', self.payload(125)).status_code, 200)
        first = self.client.get('/pessoas?formato=json').json
        last = self.client.get('/pessoas?formato=json&pagina=3').json
        self.assertEqual(first['total'], 125)
        self.assertEqual(len(first['people']), 50)
        self.assertEqual(len(last['people']), 25)
        self.assertEqual(self.client.get('/pessoas?formato=json&busca=aluno125@').json['total'], 1)
        self.assertEqual(self.client.get('/pessoas?formato=json&busca=%25').json['total'], 0)
        self.assertEqual(self.client.get('/pessoas?pagina=0').status_code, 400)
        self.assertEqual(self.client.get('/pessoas').status_code, 200)
        with Session(self.engine) as db:
            self.assertIsNotNone(db.scalar(select(Audit).where(Audit.action == 'pessoas_consultadas')))

    def test_received_minus_expenses_and_school_isolation(self):
        one, two = self.school(), self.school('teste02')
        self.assertEqual(self.entry(one)[0].status_code, 200)
        self.assertEqual(self.entry(one, 'despesa', '120,55')[0].status_code, 200)
        self.assertEqual(self.entry(two, 'despesa', '30.10')[0].status_code, 200)
        response = self.client.get('/?formato=json').json
        self.assertEqual(response['totals']['receita'], 50000)
        self.assertEqual(response['totals']['despesa'], 15065)
        self.assertEqual(response['totals']['lucro'], 34935)
        self.assertEqual(next(r for r in response['schools'] if r['id'] == two)['lucro'], -3010)
        other = '2020-01' if today().year != 2020 else '2019-01'
        self.assertEqual(self.client.get('/?formato=json&mes=' + other).json['totals']['receita'], 0)
        for month in ['2026-13', 'x', '0000-01']:
            self.assertEqual(self.client.get('/?mes=' + month).status_code, 400)

    def test_movement_idempotence_and_invalid_money_no_implicit_receipt(self):
        sid = self.school()
        self.assertEqual(self.client.get('/?formato=json').json['totals']['receita'], 0)
        result, data = self.entry(sid)
        repeated = self.post(f'/escolas/{sid}/movimentos', data)
        self.assertEqual(repeated.json['id'], result.json['id'])
        changed = dict(data, amount='501')
        self.assertEqual(self.post(f'/escolas/{sid}/movimentos', changed).status_code, 409)
        for amount in ['NaN', '-10', '1e3', '10,009', '0', '1.000,00']:
            self.assertEqual(self.entry(sid, amount=amount)[0].status_code, 400)
        self.assertEqual(self.entry(sid, day=(today() + timedelta(days=1)).isoformat())[0].status_code, 400)
        self.assertEqual(self.entry(sid, request_key='invalid')[0].status_code, 400)
        self.assertEqual(self.entry(sid, kind=[])[0].status_code, 400)
        self.assertEqual(self.client.get('/?formato=json').json['totals']['receita'], 50000)

    def test_cancel_keeps_history_and_excludes_amount(self):
        sid = self.school()
        result, _ = self.entry(sid)
        mid = result.json['id']
        self.assertEqual(self.post(f'/movimentos/{mid}/cancelar', dict(reason='Duplicidade conferida')).status_code, 200)
        self.assertEqual(self.post(f'/movimentos/{mid}/cancelar', dict(reason='Duplicidade conferida')).status_code, 409)
        self.assertEqual(self.client.get('/?formato=json').json['totals']['receita'], 0)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Movement, mid).cents, 50000)
            self.assertIsNotNone(db.get(Movement, mid).cancelled_at)

    def test_cli_integration_key_rotates_without_disclosing_token_and_exports(self):
        sid = self.school()
        with TemporaryDirectory() as temp:
            output = Path(temp) / 'token'
            result = self.runner.invoke(args=['integration-key', 'teste01', '--output', str(output)])
            self.assertEqual(result.exit_code, 0, result.output)
            token = output.read_text().strip()
            self.assertNotIn(token, result.output)
            self.assertEqual(self.integrate('teste01', self.payload(), token).status_code, 200)
            self.assertNotEqual(self.runner.invoke(args=['integration-key', 'teste01', '--output', str(output)]).exit_code, 0)
            second = Path(temp) / 'newtoken'
            self.assertEqual(self.runner.invoke(args=['integration-key', 'teste01', '--rotate', '--output', str(second)]).exit_code, 0)
            self.assertEqual(self.integrate('teste01', self.payload(), token).status_code, 401)
            export = Path(temp) / 'manifest.json'
            result = self.runner.invoke(args=['export-schools', '--project', 'edufast-nuvem', '--platform-host', 'painel.example.test', '--image',
                'ghcr.io/samucau1/edufast-2.0@sha256:' + 'a'*64, '--output', str(export)])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(json.loads(export.read_text())['schools'], [dict(id='teste01', host='teste01.example.test')])

    def test_startup_never_creates_schema_or_accepts_school_secret(self):
        with TemporaryDirectory() as temp:
            url = 'sqlite:///' + str(Path(temp) / 'empty.db')
            with self.assertRaisesRegex(RuntimeError, 'pendente'):
                create_app(dict(DATABASE_URL=url, SECRET_KEY='independent-central-key-' + 'x'*32, PLATFORM_ENV='development'))
            engine = create_engine(url)
            self.assertEqual(inspect(engine).get_table_names(), [])
            engine.dispose()
        with self.assertRaises(RuntimeError):
            create_app(dict(SECRET_KEY='', DATABASE_URL='sqlite:///:memory:'))
        self.assertNotIn('usuarios', Base.metadata.tables)
        self.assertIn('PROPOSTA', proposed_sql())
        proposal = Path(control_plane.__file__).resolve().parent / 'migrations/001_central.sql'
        self.assertEqual(proposal.read_text(encoding='utf-8'), proposed_sql())

    def parallel_posts(self, actions):
        def run(action):
            client = self.app.test_client()
            with client.session_transaction() as cookie:
                cookie.update(platform_owner=1, owner_version=1, csrf_token='test-thread-csrf')
            return client.post(action[0], json=action[1], headers={'X-CSRF-Token': 'test-thread-csrf'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, actions))

    def test_postgresql_concurrent_finance_cannot_duplicate_request(self):
        if self.engine.dialect.name != 'postgresql':
            self.skipTest('Concorrencia real exige PostgreSQL do executor descartavel')
        sid = self.school()
        data = dict(kind='receita', amount='500', day=today().isoformat(), description='Concorrencia', request_key=str(uuid4()))
        actions = [(f'/escolas/{sid}/movimentos', data)] * 2
        statuses = self.parallel_posts(actions)
        self.assertIn(200, statuses)
        self.assertTrue(all(code in {200, 409} for code in statuses), statuses)
        self.assertEqual(self.client.get('/?formato=json').json['totals']['receita'], 50000)

    def test_postgresql_concurrent_school_edits_conflict(self):
        if self.engine.dialect.name != 'postgresql':
            self.skipTest('Concorrencia real exige PostgreSQL do executor descartavel')
        sid = self.school()
        body = dict(name='Edicao concorrente', monthly='100', state='ativa', version=1)
        self.assertEqual(sorted(self.parallel_posts([(f'/escolas/{sid}', body)] * 2)), [200, 409])

    def test_publisher_reads_two_disposable_schools_without_sensitive_fields(self):
        from two_school_test_data import initialize
        from app.platform_publish import directory
        for slug in ['teste01', 'teste02']:
            engine = create_engine('sqlite:///:memory:')
            initialize(engine, slug)
            with Session(engine) as db:
                payload = directory(db)
            self.assertEqual(len(payload['people']), 26)
            self.assertEqual(sum(p['role'] == 'professor' for p in payload['people']), 5)
            self.assertEqual(sum(p['role'] == 'aluno' for p in payload['people']), 20)
            self.assertTrue(all(set(person) == {'local_id', 'name', 'email', 'role', 'state'} for person in payload['people']))
            sid = self.school(slug)
            self.key(sid, slug)
            self.assertEqual(self.integrate(slug, payload, slug).status_code, 200)
            engine.dispose()
        self.assertEqual(self.client.get('/pessoas?formato=json').json['total'], 52)


if __name__ == '__main__':
    unittest.main()
