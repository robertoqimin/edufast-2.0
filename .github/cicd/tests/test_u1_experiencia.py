"""U1 (plano de UX): mensagens claras, erros sem JSON cru no navegador, estado visível e acessibilidade."""
import re
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

import test_concurrency as fixtures
import test_estudos as study
import app as app_package

APP = Path(app_package.__file__).resolve().parent
SEM_ACENTO = re.compile(r'\b(nao|sao|invalid[oa]s?|ja|Permissao|Solicitacao|disponivel|obrigatori[oa]s?|Operacao|alteracao|'
                        r'aprovacao|usuario|vinculos?|codigo|matricula|historico|materias?|formulario|horaria|possivel|sessao)\b')
LITERAL = re.compile(r"""(?:MutationConflict\(\s*f?|abort\(\s*\d+\s*,\s*f?|["'](?:erro|mensagem)["']\s*:\s*f?|flash\(\s*f?)(["'])((?:(?!\1).)*)\1""")
HTML = {'Accept': 'text/html'}


class MensagensTests(TestCase):
    def test_nenhuma_mensagem_ao_usuario_sem_acento(self):
        achadas = []
        for path in APP.rglob('*.py'):
            for numero, linha in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                for _, texto in LITERAL.findall(linha):
                    if SEM_ACENTO.search(re.sub(r'\{[^}]*\}', '', texto)):
                        achadas.append(f'{path.relative_to(APP)}:{numero}: {texto}')
        self.assertEqual(achadas, [])


class ErrosNoNavegadorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_formulario_com_erro_mostra_pagina_e_volta_ao_formulario(self):
        dados = {'turma_id': '1', 'disciplina_id': '1', 'titulo': '', 'idempotency_key': uuid4().hex}
        navegador = self.fixture.client(3).post('/professor/atividades/lancar', data=dados,
            headers={**HTML, 'Referer': 'http://localhost/professor/dashboard'})
        self.assertEqual(navegador.status_code, 400)
        html = navegador.get_data(as_text=True)
        self.assertIn('Não foi possível concluir esta ação', html)
        self.assertIn('Voltar e corrigir', html)
        self.assertIn('href="/professor/dashboard"', html)
        self.assertNotIn('{"erro"', html)

    def test_cliente_de_api_continua_recebendo_json(self):
        dados = {'turma_id': '1', 'disciplina_id': '1', 'titulo': '', 'idempotency_key': uuid4().hex}
        api = self.fixture.client(3).post('/professor/atividades/lancar', data=dados, headers={'Accept': 'application/json'})
        self.assertEqual(api.status_code, 400)
        self.assertIn('erro', api.get_json())

    def test_voltar_nunca_leva_para_outro_site(self):
        dados = {'turma_id': '1', 'disciplina_id': '1', 'titulo': '', 'idempotency_key': uuid4().hex}
        html = self.fixture.client(3).post('/professor/atividades/lancar', data=dados,
            headers={**HTML, 'Referer': 'https://exemplo-malicioso.test/x'}).get_data(as_text=True)
        self.assertNotIn('exemplo-malicioso', html)
        self.assertNotIn('Voltar e corrigir', html)

    def test_envio_do_professor_confirma_na_tela(self):
        dados = {'turma_id': '1', 'disciplina_id': '1', 'titulo': 'Lista 1', 'idempotency_key': uuid4().hex}
        client = self.fixture.client(3)
        self.assertEqual(client.post('/professor/atividades/lancar', data=dados).status_code, 302)
        self.assertIn('Solicitação enviada para aprovação', client.get('/professor/dashboard').get_data(as_text=True))

    def test_acessibilidade_do_formulario_de_atividade_e_menu(self):
        html = self.fixture.client(3).get('/professor/dashboard').get_data(as_text=True)
        for rotulo in ('Disciplina da atividade', 'Data de entrega (opcional)', 'Anexo da atividade (opcional)'):
            self.assertIn(f'aria-label="{rotulo}"', html)
        script = (APP / 'static/js/compartilhado/shell_react.js').read_text(encoding='utf-8')
        self.assertIn('tab.classList.toggle("active", ativa)', script)

    def test_cadastro_de_admin_nao_pede_nome_descartado(self):
        from app.database import get_session
        from app.models import UsuarioModel
        with get_session() as db:
            db.add(UsuarioModel(id=9, email='super@example.test', senha='-', tipo='super_admin'))
            db.commit()
        client = self.app.test_client()
        with client.session_transaction() as s:
            s.update(user_id=9, user_role='super_admin', user_email='super@example.test', auth_version=0)
        self.assertIn('data-academic="nome">Nome completo', client.get('/super/usuarios').get_data(as_text=True))


class EstadoVisivelTests(TestCase):
    setUpClass = classmethod(lambda cls: study.StudyTests.setUpClass.__func__(cls))
    setUp = study.StudyTests.setUp
    client = study.StudyTests.client
    post = study.StudyTests.post
    create = study.StudyTests.create
    propose = study.StudyTests.propose

    def test_professor_ve_rascunho_e_aguardando_aprovacao(self):
        rid = self.create().json['id']
        self.assertIn('Rascunho — só você vê', self.client().get('/estudos/disciplinas/1').get_data(as_text=True))
        self.assertEqual(self.propose(rid).status_code, 202)
        self.assertIn('Aguardando aprovação da secretaria', self.client().get('/estudos/disciplinas/1').get_data(as_text=True))

    def test_curso_publicado_sem_turma_explica_o_que_falta(self):
        import test_cursos_ms04 as ms04
        cid = ms04.CourseApiTests.create(self)
        html = self.client().get(f'/aprendizagem/cursos/{cid}').get_data(as_text=True)
        self.assertIn('Depois de publicado, a secretaria libera o curso para a turma.', html)
