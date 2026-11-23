"""Contratos HTML MS04 nas mesmas regras e transações da API."""
from unittest import TestCase
from uuid import uuid4
from sqlalchemy import inspect
import test_cursos_ms04 as api
from app.database import get_session, engine
from app.models import RetomadaCursoModel, ProgressoAulaModel


class CourseFrontendTests(TestCase):
    setUpClass = classmethod(api.CourseApiTests.setUpClass.__func__)
    setUp = api.CourseApiTests.setUp
    client = api.CourseApiTests.client
    post = api.CourseApiTests.post
    decide = api.CourseApiTests.decide
    create = api.CourseApiTests.create
    edit = api.CourseApiTests.edit
    version = api.CourseApiTests.version
    tree = api.CourseApiTests.tree
    publish = api.CourseApiTests.publish

    def form(self,path,data,uid=3,key=None):
        return self.client(uid).post(path+'?interface=web',data={
            'csrf_token':'study-csrf','idempotency_key':key or uuid4().hex,**data})

    def test_library_editor_and_text_are_html_escaped(self):
        cid,m,c,lessons = self.tree()
        for antigo,novo in (('/cursos','/aprendizagem'),(f'/cursos/{cid}',f'/aprendizagem/cursos/{cid}')):
            self.assertEqual(self.client().get(antigo).location,novo)  # B2: páginas antigas redirecionam
        for path in ('/aprendizagem',f'/aprendizagem/cursos/{cid}',
                f'/aprendizagem/cursos/{cid}/aulas/{lessons[0]}',f'/aprendizagem/cursos/{cid}/capitulos/{c}/aulas/nova'):
            r = self.client().get(path)
            self.assertEqual(r.status_code,200,r.text)
            self.assertIn('text/html',r.content_type)
        r = self.client().get(f'/aprendizagem/cursos/{cid}/aulas/{lessons[0]}')
        self.assertIn('&lt;script&gt;',r.text)
        self.assertNotIn('<script>fict',r.text)
        self.assertEqual(self.client(2).get(f'/aprendizagem/cursos/{cid}').status_code,403)
        self.assertEqual(self.client(4).get(f'/aprendizagem/cursos/{cid}').status_code,403)

    def test_web_create_edit_replay_and_lesson_destinations(self):
        r = self.form('/api/cursos',{'disciplina_id':1,'titulo':'HTML'})
        self.assertEqual(r.status_code,303,r.text)
        self.assertIn('/aprendizagem/cursos/',r.location)
        cid = int(r.location.rsplit('/',1)[1])
        data = {'versao':1,'acao':'adicionar','tipo':'capitulo','titulo':'Módulo'}
        first = self.form(f'/api/cursos/{cid}/estrutura',data,key='html')
        replay = self.form(f'/api/cursos/{cid}/estrutura',data,key='html')
        self.assertEqual(first.location,replay.location)
        self.assertEqual(replay.status_code,303)
        self.assertEqual(self.form(f'/api/cursos/{cid}/estrutura',data).status_code,409)
        with get_session() as db:
            from app.models import CapituloModel
            mid = db.query(CapituloModel.id).filter_by(curso_id=cid).scalar()
        chap = self.edit(cid,acao='adicionar',tipo='tema',pai_id=mid,titulo='Capítulo')['item_id']
        r = self.form(f'/api/cursos/{cid}/estrutura',{'versao':self.version(cid),
            'acao':'adicionar','tipo':'aula','pai_id':chap,'titulo':'Texto','tipo_aula':'texto','corpo':'Conteúdo','video':''})
        self.assertEqual(r.status_code,303,r.text)
        self.assertIn('/aulas/',r.location)
        self.assertEqual(self.client().get(r.location).status_code,200)

    def test_read_does_not_change_resume_open_and_completion_are_separate(self):
        cid,m,c,lessons = self.tree()
        offer = self.publish(cid)
        r = self.client(2).get(f'/aprendizagem/ofertas/{offer}')
        self.assertEqual(r.status_code,200,r.text)
        self.assertIn('Abrir aula',r.text)
        with get_session() as db:
            self.assertEqual(db.query(RetomadaCursoModel).count(),0)
        r = self.form(f'/api/aprender/{offer}/aulas/{lessons[1]}/abrir',{'versao':0},uid=2)
        self.assertEqual(r.status_code,303,r.text)
        self.assertEqual(r.location,f'/aprendizagem/ofertas/{offer}?aula={lessons[1]}')
        page = self.client(2).get(r.location)
        self.assertIn('&lt;script&gt;',page.text)
        self.assertIn('Marcar como concluída',page.text)
        with get_session() as db:
            self.assertEqual(db.query(ProgressoAulaModel).count(),0)
        r = self.form(f'/api/aprender/{offer}/aulas/{lessons[1]}/concluir',{},uid=2)
        self.assertEqual(r.status_code,303)
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}').json['retomada']['aula_id'],lessons[1])
        self.assertIn('Aula concluída',self.client(2).get(r.location).text)

    def test_html_errors_csrf_and_json_contract(self):
        cid = self.create()
        path = f'/api/cursos/{cid}/estrutura'
        r = self.client().post(path+'?interface=web',data={'versao':1})
        self.assertEqual(r.status_code,403)
        self.assertIn('text/html',r.content_type)
        self.assertIn('CSRF',r.text)
        r = self.post(path+'?interface=web',{'versao':1,'acao':'curso','titulo':'JSON'})
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.is_json)
        self.assertEqual(self.form(path,{'versao':1,'acao':'curso','titulo':'Obsoleto'}).status_code,409)

    def test_publication_offers_and_review_html(self):
        cid,m,c,lessons = self.tree(count=1)
        r = self.form(f'/api/cursos/{cid}/solicitar-publicacao',{'versao':self.version(cid)})
        self.assertEqual(r.status_code,303,r.text)
        review = self.client(1).get('/solicitacoes')
        self.assertIn('Conferir curso',review.text)
        self.assertNotIn('snapshot',review.text)
        from app.models import SolicitacaoAlteracaoModel
        with get_session() as db:
            pid = db.query(SolicitacaoAlteracaoModel.id).filter_by(tipo='publicar_curso').scalar()
        self.assertEqual(self.decide(pid).status_code,200)
        r = self.form(f'/api/cursos/{cid}/ofertas',{'versao':self.version(cid),'turma_disciplina_id':1,'ativa':'true'},uid=1)
        self.assertEqual(r.status_code,303,r.text)
        r = self.client(1).get(r.location)
        self.assertEqual(r.status_code,200,r.text)
        self.assertIn('Acesso ativo',r.text)
        self.assertIn('Cursos',self.client(2).get('/estudos/disciplinas/1').text)
        self.assertEqual(self.client(2).get('/aprendizagem/disciplinas/1').status_code,200)

    def test_missing_optional_schema_keeps_legacy_library(self):
        from app.models import CursoVersaoModel, RetomadaCursoModel, AulaConteudoCursoModel, RecursoAulaCursoModel
        for model in (RecursoAulaCursoModel,RetomadaCursoModel,AulaConteudoCursoModel,CursoVersaoModel):
            model.__table__.drop(engine)
        self.assertEqual(self.client().get('/cursos').status_code,200)
        self.assertEqual(self.client().get('/aprendizagem').status_code,503)
        self.assertNotIn('curso_versoes',inspect(engine).get_table_names())
