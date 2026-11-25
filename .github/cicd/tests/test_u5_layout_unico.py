"""U5 (plano de UX, O3): uma aparência e um caminho por tarefa.

Todas as telas no layout padrão; uma tela de turma (a antiga foi aposentada); Solicitações com
filtro e nome de quem enviou e decidiu.
"""
import re
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

import test_concurrency as fixtures
import app as app_package
from app.database import get_session
from app.models import SolicitacaoAlteracaoModel

APP = Path(app_package.__file__).resolve().parent
# Fora do gestao_base, com cabeçalho padrão próprio (permitido pelo protocolo): a própria base,
# o login (tela pública) e Usuários e permissões (tela de referência do design system).
ESTRUTURA_PROPRIA = {'gestao_base.html', 'login.html', 'super_usuarios.html'}
CSRF = 'u5-csrf'


class LayoutUnicoTests(TestCase):
    def test_todas_as_telas_no_layout_padrao(self):
        telas = sorted(p.name for p in (APP / 'templates').glob('*.html'))
        fora = [t for t in telas if "{% extends 'gestao_base.html' %}" not in (APP / 'templates' / t).read_text(encoding='utf-8')]
        self.assertEqual(sorted(fora), sorted(ESTRUTURA_PROPRIA))
        for t in ESTRUTURA_PROPRIA - {'gestao_base.html'}:
            self.assertIn('workspace_head.html', (APP / 'templates' / t).read_text(encoding='utf-8'), t)
        self.assertGreaterEqual(len(telas), 58)

    def test_sem_montagem_por_template_nem_selo_falso(self):
        for arquivo in (APP / 'templates').rglob('*.html'):
            texto = arquivo.read_text(encoding='utf-8')
            with self.subTest(arquivo=arquivo.name):
                self.assertNotIn('data-react-shell', texto)
                self.assertNotIn('Online agora', texto)
                self.assertNotIn('Admin Secretaria', texto)
        self.assertFalse((APP / 'templates/admin_turmas.html').exists())
        self.assertFalse((APP / 'static/css/painel.css').exists())

    def test_menu_tem_uma_entrada_de_turma(self):
        menu = (APP / 'templates/partials/workspace_sidebar.html').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r"nav_link\('cursos\.gestao_turmas', 'Turmas'", menu)), 1)
        self.assertNotIn("'home.admin_turmas'", menu)
        self.assertNotIn("'Gestão acadêmica'", menu)


class TelasNoServidorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def cliente(self, user):
        client = self.fixture.client(user)
        with client.session_transaction() as session:
            session['csrf_token'] = CSRF
        return client

    def test_telas_migradas_abrem_com_menu_titulo_e_conteudo(self):
        for user, path, titulo in [(1, '/admin/disciplinas', 'Disciplinas'), (1, '/admin/banco-de-dados', 'Registros acadêmicos'),
                                   (1, '/admin/comunicados', 'Comunicados'), (1, '/admin/cadastro-alunos', 'Cadastro de alunos'),
                                   (1, '/admin/cadastro-professores', 'Cadastro de professores'), (1, '/admin/alunos/1', 'Detalhes do aluno'),
                                   (1, '/admin/professores/1', 'Detalhes do professor'), (3, '/professor/dashboard', 'Olá, Prof. Professor!'),
                                   (2, '/aluno/dashboard', 'Olá, Aluno!')]:
            with self.subTest(path=path):
                r = self.cliente(user).get(path)
                self.assertEqual(r.status_code, 200)
                html = r.get_data(as_text=True)
                self.assertIn('class="workspace-sidebar"', html)
                self.assertIn(f'<h1>{titulo}</h1>', html)
                self.assertIn('class="page-heading"', html)
                self.assertNotIn('<template', html)
                self.assertNotIn('| Educa Fast', html)

    def test_turmas_mostra_materias_professores_e_alunos(self):
        client = self.cliente(1)
        r = client.post('/admin/gestao-turmas', data={'acao': 'atribuir', 'turma_id': 1, 'disciplina_id': 1, 'professor_id': 1, 'csrf_token': CSRF})
        self.assertEqual(r.status_code, 302)
        html = client.get('/admin/gestao-turmas').get_data(as_text=True)
        self.assertIn('<h1>Turmas</h1>', html)
        self.assertIn('<strong>Matematica</strong>', html)
        self.assertIn('Professor · Ativo', html)
        self.assertIn('>Aluno</a>', html)                      # aluno matriculado, com link para o detalhe
        self.assertIn('1 aluno ·', html)

    def test_solicitacoes_filtra_e_mostra_nomes(self):
        professor = self.cliente(3)
        r = professor.post('/academico/avaliacoes/1/alunos/1', json={'valor': '8', 'versao': 0},
                           headers={'X-CSRF-Token': CSRF, 'Idempotency-Key': uuid4().hex})
        with get_session() as db:
            db.add(SolicitacaoAlteracaoModel(solicitante_id=3, tipo='criar_turma', payload='{}', estado='rejeitada',
                                             decidido_por=1, justificativa='Duplicada'))
            db.commit()
        secretaria = self.cliente(1)
        pendentes = secretaria.get('/solicitacoes').get_data(as_text=True)
        self.assertIn('aria-current="page">Pendentes', pendentes)
        self.assertNotIn('Duplicada', pendentes)
        decididas = secretaria.get('/solicitacoes?estado=decididas').get_data(as_text=True)
        self.assertIn('Duplicada', decididas)
        self.assertIn('Enviada por: Professor (professor)', decididas)
        self.assertIn('Decidida por u1@example.test (secretaria)', decididas)
        self.assertIn('Decididas (1)', decididas)
        self.assertIn('Todas (', decididas)
        self.assertEqual(secretaria.get('/solicitacoes?estado=xyz').status_code, 200)
