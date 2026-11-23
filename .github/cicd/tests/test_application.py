"""Contratos de integração em banco descartável, executados em SQLite e PostgreSQL."""
import io
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app
from app.database import Base, engine, get_session
from app.models import UsuarioModel, TurmaModel, DisciplinaModel


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    def setUp(self):
        # Somente a instância descartável criada por ci.py recebe esta suíte.
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.client = self.app.test_client()
        db = get_session()
        db.add(UsuarioModel(email='admin@example.test', senha=generate_password_hash('test-password-123'), tipo='admin'))
        db.commit()
        db.close()

    def login(self):
        return self.client.post('/login', json={'email': 'admin@example.test', 'senha': 'test-password-123'})

    def test_browser_session_probe_requires_cookie_and_revalidates_account(self):
        self.assertEqual(self.client.get('/auth/session').status_code, 401)
        login = self.login()
        response = self.client.get('/auth/session')
        self.assertEqual(response.json, {'authenticated': True, 'role': 'admin'})
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get('/auth/session', headers={
            'Authorization': 'Bearer ' + login.json['token']}).status_code, 401)
        with get_session() as db:
            db.query(UsuarioModel).filter_by(email='admin@example.test').update({'estado': 'pendente'})
            db.commit()
        self.assertEqual(self.client.get('/auth/session').status_code, 401)

    def test_health_checks_database(self):
        self.assertEqual(self.client.get('/healthz').json['status'], 'ok')

    def test_health_fails_when_database_unavailable(self):
        with patch('app.engine.connect', side_effect=RuntimeError('test outage')):
            self.assertEqual(self.client.get('/healthz').status_code, 503)

    def test_login_page(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_admin_pages_require_authentication(self):
        for path in ['/admin/dashboard', '/admin/turmas', '/admin/disciplinas', '/admin/banco-de-dados']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_login_and_admin_navigation(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['token'])
        for path in ['/admin/dashboard', '/admin/turmas', '/admin/disciplinas', '/admin/comunicados', '/admin/banco-de-dados', '/admin/cadastro-alunos', '/admin/cadastro-professores']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_invalid_password(self):
        response = self.client.post('/login', json={'email': 'admin@example.test', 'senha': 'wrong'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 403)

    def test_logout_revokes_web_session(self):
        self.login()
        self.client.get('/logout')
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 403)

    def test_create_turma_persists_and_duplicate_is_rejected(self):
        self.login()
        form = {'nome': 'Turma CI', 'codigo': 'CI-A', 'ano_letivo': '2026', 'turno': 'Manhã'}
        self.assertEqual(self.client.post('/admin/turmas', data=form).status_code, 302)
        self.client.post('/admin/turmas', data=form)
        db = get_session()
        try:
            self.assertEqual(db.query(TurmaModel).filter_by(codigo='CI-A').count(), 1)
        finally:
            db.close()

    def test_create_disciplina(self):
        self.login()
        response = self.client.post('/admin/disciplinas', data={'nome': 'Matemática', 'codigo': 'MAT-CI', 'carga_horaria': '80'})
        self.assertEqual(response.status_code, 302)
        db = get_session()
        try:
            self.assertEqual(db.query(DisciplinaModel).filter_by(codigo='MAT-CI').count(), 1)
        finally:
            db.close()

    def test_create_student_and_login_as_student(self):
        self.login()
        response = self.client.post('/cadastro/alunos', json={'nome': 'Aluno CI', 'email': 'aluno@example.test', 'senha': 'test-password-123', 'matricula': 'CI001'})
        self.assertEqual(response.status_code, 201)
        self.client.get('/logout')
        response = self.client.post('/login', json={'email': 'aluno@example.test', 'senha': 'test-password-123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/aluno/dashboard').status_code, 200)
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 403)

    def test_create_teacher_and_jwt_authorization(self):
        self.login()
        response = self.client.post('/cadastro/professores', json={'nome': 'Professor CI', 'email': 'prof@example.test', 'senha': 'test-password-123', 'cpf': '12345678901'})
        self.assertEqual(response.status_code, 201)
        self.client.get('/logout')
        response = self.client.post('/login', json={'email': 'prof@example.test', 'senha': 'test-password-123'})
        headers = {'Authorization': 'Bearer '+response.json['token']}
        self.assertEqual(self.client.get('/professor/teste', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/professor/dashboard').status_code, 200)
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 403)

    def test_missing_and_tampered_jwt_rejected(self):
        self.assertEqual(self.client.get('/professor/teste').status_code, 401)
        self.assertEqual(self.client.get('/professor/teste', headers={'Authorization': 'Bearer invalid.token.signature'}).status_code, 401)

    def test_admin_registration_requires_admin(self):
        self.assertEqual(self.client.post('/cadastro/alunos', json={}).status_code, 403)
        self.assertEqual(self.client.post('/cadastro/professores', json={}).status_code, 403)

    def test_create_admin_preserves_existing_accounts(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(args=['create-admin', '--email', 'second@example.test', '--password', 'another-password-123'])
        self.assertEqual(result.exit_code, 0, result.output)
        duplicate = runner.invoke(args=['create-admin', '--email', 'second@example.test', '--password', 'do-not-replace-123'])
        self.assertNotEqual(duplicate.exit_code, 0)
        db = get_session()
        try:
            self.assertEqual(db.query(UsuarioModel).count(), 2)
        finally:
            db.close()

    def test_create_admin_rejects_weak_password(self):
        result = self.app.test_cli_runner().invoke(args=['create-admin', '--email', 'second@example.test', '--password', '123'])
        self.assertNotEqual(result.exit_code, 0)

    def test_upload_limit(self):
        self.app.config['MAX_CONTENT_LENGTH'] = 100
        try:
            self.assertEqual(self.client.post('/cadastro', data={'arquivo': (io.BytesIO(b'x'*200), 'test.txt')}).status_code, 413)
        finally:
            self.app.config['MAX_CONTENT_LENGTH'] = 16*1024*1024

    def test_production_refuses_weak_secret_and_missing_hosts(self):
        from config import Config
        with patch.object(Config, 'APP_ENV', 'production'), patch.object(Config, 'SECRET_KEY', 'weak'):
            with self.assertRaises(RuntimeError):
                create_app()
        with patch.object(Config, 'APP_ENV', 'production'), patch.object(Config, 'SECRET_KEY', 'x'*64), patch.object(Config, 'TRUSTED_HOSTS', None):
            with self.assertRaises(RuntimeError):
                create_app()

    def test_production_proxy_and_cookie(self):
        from config import Config
        with patch.object(Config, 'APP_ENV', 'production'), patch.object(Config, 'SECRET_KEY', 'x'*64), patch.object(Config, 'TRUSTED_HOSTS', ['localhost']), patch.object(Config, 'SESSION_COOKIE_SECURE', True):
            production = create_app()
        client = production.test_client()
        response = client.post('/login', json={'email': 'admin@example.test', 'senha': 'test-password-123'}, headers={'X-Forwarded-Proto': 'https'})
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['Set-Cookie']
        for flag in ['Secure', 'HttpOnly', 'SameSite=Lax']:
            self.assertIn(flag, cookie)
        self.assertEqual(client.get('/healthz', headers={'Host': 'unexpected.test'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
