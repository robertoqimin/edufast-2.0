"""Correcoes de seguranca S1-S7 (23/11/2026): limitador de login, resposta unica,
regra de senha, cabecalhos HTTP e cache de paginas de usuario."""
import re
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import text

import test_concurrency as fixtures
from app.database import get_session
from app.models import UsuarioModel
from app.services import limite_login_service

SENHA = 'test-password-123'


class SegurancaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def login(self, email, senha, ip='10.0.0.1'):
        return self.app.test_client().post('/login', json={'email': email, 'senha': senha},
                                           environ_base={'REMOTE_ADDR': ip})

    # S1 — limitador de 5 tentativas por conta
    def test_five_failures_block_the_account_even_with_correct_password(self):
        for _ in range(5):
            self.assertEqual(self.login('u1@example.test', 'errada').status_code, 401)
        bloqueado = self.login('u1@example.test', SENHA)
        self.assertEqual(bloqueado.status_code, 429)
        self.assertEqual(int(bloqueado.headers['Retry-After']), 15 * 60)
        self.assertNotIn('retry_after', bloqueado.json)
        self.assertEqual(self.login('u3@example.test', SENHA).status_code, 200)  # outra conta segue livre

    def test_block_expires_after_the_window(self):
        agora = 1_800_000_000.0
        with patch.object(limite_login_service.time, 'time', return_value=agora):
            for _ in range(5):
                self.login('u1@example.test', 'errada')
            self.assertEqual(self.login('u1@example.test', SENHA).status_code, 429)
        with patch.object(limite_login_service.time, 'time', return_value=agora + 15 * 60):
            self.assertEqual(self.login('u1@example.test', SENHA).status_code, 200)

    def test_correct_password_resets_the_account_counter(self):
        for _ in range(4):
            self.login('u1@example.test', 'errada')
        self.assertEqual(self.login('u1@example.test', SENHA).status_code, 200)
        for _ in range(4):
            self.assertEqual(self.login('u1@example.test', 'errada').status_code, 401)
        self.assertEqual(self.login('u1@example.test', SENHA).status_code, 200)

    def test_ip_limit_stops_spraying_across_many_accounts(self):
        for i in range(30):
            self.login(f'tentativa{i}@example.test', 'errada', ip='10.9.9.9')
        self.assertEqual(self.login('u1@example.test', SENHA, ip='10.9.9.9').status_code, 429)
        self.assertEqual(self.login('u1@example.test', SENHA, ip='10.1.1.1').status_code, 200)

    def test_expired_rows_are_cleaned_up(self):
        agora = 1_800_000_000.0
        with patch.object(limite_login_service.time, 'time', return_value=agora):
            for i in range(3):
                self.login(f'antigo{i}@example.test', 'errada', ip=f'10.5.5.{i}')
        with patch.object(limite_login_service.time, 'time', return_value=agora + 16 * 60):
            self.login('novo@example.test', 'errada', ip='10.6.6.6')
        with get_session() as db:
            self.assertEqual(db.execute(text('SELECT count(*) FROM limites_login')).scalar(), 2)

    def test_stored_keys_do_not_reveal_email_or_ip(self):
        self.login('u1@example.test', 'errada', ip='10.4.4.4')
        with get_session() as db:
            chaves = [r[0] for r in db.execute(text('SELECT chave FROM limites_login'))]
        self.assertEqual(len(chaves), 2)
        for chave in chaves:
            self.assertRegex(chave, r'^[0-9a-f]{64}$')
            self.assertNotIn('example', chave)

    # S6 — mesma resposta para conta inexistente e senha errada
    def test_unknown_account_and_wrong_password_are_indistinguishable(self):
        inexistente = self.login('ninguem@example.test', 'errada')
        errada = self.login('u1@example.test', 'errada')
        self.assertEqual((inexistente.status_code, inexistente.json), (errada.status_code, errada.json))
        self.assertEqual(inexistente.status_code, 401)
        for _ in range(4):
            self.login('ninguem@example.test', 'errada')
        self.assertEqual(self.login('ninguem@example.test', 'errada').status_code, 429)  # bloqueio igual

    # S4 — senha minima de 12 com caractere especial para todos (decisao de 24/11/2026)
    def test_public_registration_password_rule(self):
        base = {'nome': 'Candidato', 'tipo': 'aluno', 'matricula': 'NOVA-1'}
        for senha in ['ab!12', 'abc!12', 'curta-11!ab', 'semespecial1234', 'abc 1234567890', 'a' * 129 + '!']:
            with self.subTest(senha=senha):
                resposta = self.app.test_client().post('/cadastro', json={**base, 'email': 'novo@example.test', 'senha': senha})
                self.assertEqual(resposta.status_code, 400)
                self.assertIn('senha', resposta.json['erro'].lower())
        aceito = self.app.test_client().post('/cadastro', json={**base, 'email': 'novo@example.test', 'senha': 'aluno-novo-2026!'})
        self.assertEqual(aceito.status_code, 202, aceito.get_data(as_text=True))

    def test_admin_accounts_keep_twelve_characters_and_require_special(self):
        runner = self.app.test_cli_runner()
        fraca = runner.invoke(args=['create-admin', '--email', 'adm@example.test', '--password', 'semespecial12'])
        self.assertNotEqual(fraca.exit_code, 0)
        curta = runner.invoke(args=['create-admin', '--email', 'adm@example.test', '--password', 'curta!1'])
        self.assertNotEqual(curta.exit_code, 0)
        boa = runner.invoke(args=['create-admin', '--email', 'adm@example.test', '--password', 'admin-segura-2026'])
        self.assertEqual(boa.exit_code, 0, boa.output)
        with get_session() as db:
            self.assertEqual(db.query(UsuarioModel).filter_by(email='adm@example.test').count(), 1)

    # S3/S5/S7 — cabecalhos
    def test_security_headers_on_every_page(self):
        resposta = self.app.test_client().get('/')
        csp = resposta.headers['Content-Security-Policy']
        for diretiva in ["frame-ancestors 'none'", "object-src 'none'", "base-uri 'self'", "form-action 'self'"]:
            self.assertIn(diretiva, csp)
        self.assertRegex(csp, r"script-src 'self' 'nonce-[A-Za-z0-9_-]+'")
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertEqual(resposta.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(resposta.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(resposta.headers['Referrer-Policy'], 'strict-origin-when-cross-origin')

    def test_inline_script_carries_the_response_nonce(self):
        cliente = self.fixture.client(1)
        resposta = cliente.get('/cadastro/alunos')
        self.assertEqual(resposta.status_code, 200)
        nonce = re.search(r"'nonce-([^']+)'", resposta.headers['Content-Security-Policy']).group(1)
        html = resposta.get_data(as_text=True)
        embutidos = re.findall(r'<script(?![^>]*\bsrc=)([^>]*)>', html)
        self.assertTrue(embutidos)
        for atributos in embutidos:
            self.assertIn(f'nonce="{nonce}"', atributos)
        self.assertNotEqual(nonce, re.search(r"'nonce-([^']+)'", cliente.get('/cadastro/alunos').headers['Content-Security-Policy']).group(1))

    def test_platform_panel_has_the_same_headers(self):
        from control_plane import create_app as criar_painel
        from control_plane.models import Base as BaseCentral
        painel = criar_painel(dict(TESTING=True, DATABASE_URL='sqlite:///:memory:', PLATFORM_ENV='development',
                                   SECRET_KEY='central-only-synthetic-secret-' + 'x' * 32, SESSION_COOKIE_SECURE=False))
        BaseCentral.metadata.create_all(painel.extensions['platform_engine'])
        resposta = painel.test_client().get('/login')
        self.assertIn("frame-ancestors 'none'", resposta.headers['Content-Security-Policy'])
        self.assertEqual(resposta.headers['X-Frame-Options'], 'DENY')
        cliente = painel.test_client()
        with cliente.session_transaction() as sessao:
            sessao['platform_owner'] = 1
        logado = cliente.get('/login')
        self.assertIn('no-store', logado.headers['Cache-Control'])
        self.assertIn('Cookie', logado.headers.get('Vary', ''))
        painel.extensions['platform_engine'].dispose()

    def test_logged_user_pages_are_never_cached(self):
        resposta = self.fixture.client(1).get('/admin/disciplinas')
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('Cookie', resposta.headers.get('Vary', ''))
        self.assertEqual(resposta.headers['Cache-Control'], 'private, no-store')
        estatico = self.app.test_client().get('/static/css/app.css')
        self.assertNotIn('no-store', estatico.headers.get('Cache-Control', ''))
        estatico.close()
