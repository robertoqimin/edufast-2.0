"""Recovered superprofile, original design and current security boundaries."""
import json
from unittest import TestCase, skipUnless
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4
from werkzeug.security import generate_password_hash
from cryptography.fernet import Fernet
import test_concurrency as fixtures
from app.database import get_session, engine
from app.models import (UsuarioModel, IdentidadeEscolaModel, CursoModel, SolicitacaoAlteracaoModel,
                        CalendarioEscolaModel, PedidoPrivacidadeModel)
from app.services.escola import IDENTIDADE_PADRAO
from config import Config


class RestoredTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        key = patch.object(Config, 'DATA_ENCRYPTION_KEY', Fernet.generate_key().decode())
        key.start(); self.addCleanup(key.stop)
        with get_session() as db:
            db.add(UsuarioModel(id=5, email='super@example.test', tipo='super_admin', senha=generate_password_hash('test-password-123')))
            db.commit()

    def client(self, user=5):
        client = self.app.test_client()
        with get_session() as db:
            row = db.get(UsuarioModel, user)
            with client.session_transaction() as s:
                s.update(user_id=user,user_role=row.tipo,user_email=row.email,auth_version=row.auth_version,csrf_token='restoration-csrf')
        return client

    def post(self, path, body, user=5, key=None):
        return self.client(user).post(path,json=body,headers={'X-CSRF-Token':'restoration-csrf','Idempotency-Key':key or uuid4().hex})

    def test_original_screens_render_and_super_navigation_exists(self):
        for path in ['/super/usuarios','/super/layout','/super/escola','/admin/dashboard','/cursos','/academico','/calendario-escolar','/mensagens','/minha-privacidade','/solicitacoes']:
            with self.subTest(path=path):
                response=self.client().get(path)
                self.assertEqual(response.status_code,200,response.get_data(as_text=True)[:300])
                self.assertIn(b'workspace-sidebar',response.data)
                self.assertIn(b'design_system.css',response.data)
                self.assertNotIn(b'cdn.tailwindcss.com',response.data)
        page=self.app.test_client().get('/')
        self.assertIn(b'login-story',page.data)
        self.assertNotIn(b'unpkg.com',page.data)

    def test_non_super_cannot_access_or_mutate_superprofile(self):
        for user in [1,2,3]:
            for path in ['/super/usuarios','/super/layout','/super/escola']:
                self.assertEqual(self.client(user).get(path).status_code,403)
            self.assertEqual(self.post('/super/escola/identidade',{**IDENTIDADE_PADRAO,'versao':0},user=user).status_code,403)

    def test_identity_persists_and_rejects_stale_or_malicious_settings(self):
        data={**IDENTIDADE_PADRAO,'versao':0,'nome':'Escola de Teste'}
        response=self.post('/super/escola/identidade',data)
        self.assertEqual(response.status_code,200,response.get_data(as_text=True))
        self.assertEqual(self.post('/super/escola/identidade',data).status_code,409)
        bad={**data,'versao':1,'destaque':'red;display:none'}
        self.assertEqual(self.post('/super/escola/identidade',bad).status_code,400)
        with get_session() as db:
            row=db.get(IdentidadeEscolaModel,1)
            self.assertEqual(row.versao,1)
            self.assertEqual(json.loads(row.dados)['nome'],'Escola de Teste')
        self.assertIn(b'Escola de Teste',self.app.test_client().get('/').data)

    def test_admin_creation_is_unique_and_requires_csrf(self):
        data={'tipo':'admin','nome':'Novo','email':'new@example.test','senha':'test-password-123','idempotency_key':'new-admin'}
        self.assertEqual(self.client().post('/super/usuarios',data=data).status_code,400)
        data['csrf_token']='restoration-csrf'
        self.assertEqual(self.client().post('/super/usuarios',data=data).status_code,302)
        self.assertEqual(self.client().post('/super/usuarios',data=data).status_code,302)
        with get_session() as db:
            self.assertEqual(db.query(UsuarioModel).filter_by(email=data['email']).count(),1)
            self.assertEqual(db.query(UsuarioModel).filter_by(email=data['email']).one().tipo,'admin')

    def test_profile_change_preserves_records_and_revokes_previous_session(self):
        old=self.client(3)
        response=self.client().post('/super/usuarios/3/perfil',data={'tipo':'admin','versao':'0','csrf_token':'restoration-csrf'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(old.get('/professor/dashboard').status_code,401)
        self.assertEqual(self.client().post('/super/usuarios/3/perfil',data={'tipo':'admin','versao':'0','csrf_token':'restoration-csrf'}).status_code,409)
        self.assertEqual(self.client().post('/super/usuarios/5/perfil',data={'tipo':'admin','versao':'0','csrf_token':'restoration-csrf'}).status_code,403)

    def test_calendar_and_school_configuration_recovered(self):
        response=self.post('/super/escola/calendarios',{'ano':2026,'nome':'Calendario','inicio':'2026-01-01','fim':'2026-12-31','dias_semana':[0,1,2,3,4],'meta_letivos':200})
        self.assertEqual(response.status_code,201,response.get_data(as_text=True))
        self.assertEqual(self.fixture.count(CalendarioEscolaModel),1)
        self.assertEqual(self.post('/super/escola/calendarios',{'ano':2026,'nome':'Duplicado','inicio':'2026-01-01','fim':'2026-12-31','dias_semana':[0],'meta_letivos':20}).status_code,409)

    def test_teacher_course_submission_waits_for_one_approval(self):
        data={'disciplina_id':1,'titulo':'Curso recuperado','descricao':'Descricao com acentos: ' + 'á' * 9000}
        key=uuid4().hex
        response=self.post('/cursos',data,user=3,key=key)
        self.assertEqual(response.status_code,202,response.get_data(as_text=True))
        self.assertEqual(self.fixture.count(CursoModel),0)
        self.assertEqual(self.post('/cursos',data,user=3,key=key).status_code,202)
        proposal=response.json['id']
        response=self.post(f'/solicitacoes/alteracoes/{proposal}/decidir',{'decisao':'aprovar'},user=1)
        self.assertEqual(response.status_code,200,response.get_data(as_text=True))
        self.assertEqual(self.fixture.count(CursoModel),1)
        self.assertEqual(self.post(f'/solicitacoes/alteracoes/{proposal}/decidir',{'decisao':'aprovar'},user=1).status_code,409)

    def test_teacher_cannot_dispatch_admin_or_unregistered_operations(self):
        for endpoint in ['gestao.usuarios','cursos.ofertar','academico.criar_periodo']:
            result=self.post('/solicitacoes/alteracoes',{'tipo':'operacao_restaurada','payload':{'endpoint':endpoint,'params':{},'payload':{}}},user=3)
            self.assertEqual(result.status_code,400)
        self.assertEqual(self.fixture.count(SolicitacaoAlteracaoModel),0)

    def test_pending_course_edit_does_not_overwrite_a_later_admin_edit(self):
        created=self.post('/cursos',{'disciplina_id':1,'professor_id':1,'titulo':'Inicial','descricao':''},user=1)
        self.assertEqual(created.status_code,201)
        course=created.json['curso_id']
        proposed=self.post(f'/cursos/{course}/estrutura',{'acao':'curso','titulo':'Proposto','descricao':''},user=3)
        self.assertEqual(proposed.status_code,202,proposed.get_data(as_text=True))
        edited=self.post(f'/cursos/{course}/estrutura',{'acao':'curso','titulo':'Alterado pelo admin','descricao':''},user=1)
        self.assertEqual(edited.status_code,200)
        self.assertEqual(self.post(f"/solicitacoes/alteracoes/{proposed.json['id']}/decidir",{'decisao':'aprovar'},user=1).status_code,409)
        with get_session() as db:
            self.assertEqual(db.get(CursoModel,course).titulo,'Alterado pelo admin')
            self.assertEqual(db.get(SolicitacaoAlteracaoModel,proposed.json['id']).estado,'pendente')

    def test_material_reviewer_can_approve_course_but_not_grade(self):
        from app.models import (AtribuicaoDocenteModel, EstadoTurmaModel, PeriodoLetivoModel,
                                AvaliacaoModel, LancamentoNotaModel)
        with get_session() as db:
            db.get(UsuarioModel,4).revisor_materiais=True
            db.add(AtribuicaoDocenteModel(professor_id=1,turma_disciplina_id=1,ativo=True))
            db.add(EstadoTurmaModel(turma_id=1,arquivada=False))
            db.add(PeriodoLetivoModel(id=1,turma_id=1,nome='Periodo',ordem=1))
            db.flush()
            db.add(AvaliacaoModel(id=1,turma_disciplina_id=1,periodo_id=1,titulo='Prova',peso=1))
            db.commit()
        course=self.post('/cursos',{'disciplina_id':1,'titulo':'Material','descricao':''},user=3)
        self.assertEqual(course.status_code,202)
        self.assertEqual(self.post(f"/solicitacoes/alteracoes/{course.json['id']}/decidir",{'decisao':'aprovar'},user=4).status_code,200)
        grade=self.post('/academico/avaliacoes/1/alunos/1',{'valor':'8','versao':0},user=3)
        self.assertEqual(grade.status_code,202,grade.get_data(as_text=True))
        self.assertEqual(self.fixture.count(LancamentoNotaModel),0)
        self.assertEqual(self.post(f"/solicitacoes/alteracoes/{grade.json['id']}/decidir",{'decisao':'aprovar'},user=4).status_code,403)
        self.assertEqual(self.post(f"/solicitacoes/alteracoes/{grade.json['id']}/decidir",{'decisao':'aprovar'},user=1).status_code,200)
        self.assertEqual(self.fixture.count(LancamentoNotaModel),1)

    def test_privacy_requests_are_scoped_and_encrypted(self):
        response=self.client(2).post('/minha-privacidade',data={'tipo':'acesso','detalhe':'Dados pessoais de teste','csrf_token':'restoration-csrf'})
        self.assertEqual(response.status_code,302,response.get_data(as_text=True))
        with get_session() as db:
            self.assertEqual(db.query(PedidoPrivacidadeModel).one().usuario_id,2)
        self.assertNotIn(b'Dados pessoais de teste',self.client(3).get('/minha-privacidade').data)

    def test_school_rules_create_periods_without_rewriting_history(self):
        from app.models import PeriodoLetivoModel
        calendar=self.post('/super/escola/calendarios',{'ano':2026,'nome':'Calendario','inicio':'2026-01-01','fim':'2026-12-31','dias_semana':[0,1,2,3,4],'meta_letivos':200}).json['calendario_id']
        response=self.post('/super/escola/politicas',{'nome':'Semestres','calendario_id':calendar,'divisao':'semestres',
            'periodos':[{'nome':'Primeiro','peso':'1','inicio':'2026-01-01','fim':'2026-06-30'},
                        {'nome':'Segundo','peso':'3','inicio':'2026-07-01','fim':'2026-12-31'}],
            'media_referencia':'7','casas':'2','arredondamento':'comercial'})
        self.assertEqual(response.status_code,201,response.get_data(as_text=True))
        policy=response.json['politica_id']
        self.assertEqual(self.post(f'/super/escola/politicas/{policy}/aplicar',{'turma_id':1}).status_code,200)
        self.assertEqual(self.post(f'/super/escola/politicas/{policy}/aplicar',{'turma_id':1}).status_code,409)
        with get_session() as db:
            self.assertEqual(db.query(PeriodoLetivoModel).count(),2)
            self.assertEqual([r.nome for r in db.query(PeriodoLetivoModel).order_by(PeriodoLetivoModel.ordem)],['Primeiro','Segundo'])

    def test_protected_superprofile_cannot_be_demoted_via_existing_api(self):
        with get_session() as db:
            db.add(UsuarioModel(id=6,email='super2@example.test',tipo='super_admin',senha='not-used'))
            db.commit()
        self.assertEqual(self.post('/admin/usuarios/6/permissoes',{'papel':'admin'}).status_code,403)

    @skipUnless(engine.dialect.name=='mysql','Concurrent updates require disposable MySQL')
    def test_two_identity_updates_have_one_effect(self):
        barrier=threading.Barrier(2)
        def update(name):
            client=self.client()
            barrier.wait(timeout=15)
            return client.post('/super/escola/identidade',json={**IDENTIDADE_PADRAO,'versao':0,'nome':name},headers={'X-CSRF-Token':'restoration-csrf'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(update,['Escola A','Escola B'])),[200,409])
        with get_session() as db:
            self.assertEqual(db.get(IdentidadeEscolaModel,1).versao,1)
