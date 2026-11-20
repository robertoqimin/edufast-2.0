"""MS04 backend/API, sem frontend e exclusivamente em banco descartável."""
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import event, inspect
import test_estudos as study
from app.database import engine, get_session, init_db
from app.models import (CursoModel, CursoVersaoModel, AulaModel, AulaConteudoCursoModel,
    RetomadaCursoModel, RecursoAulaCursoModel, ProgressoAulaModel, AuditoriaCursoModel,
    AlunoDisciplinaModel, AlunoTurmaModel, AlunoModel, ProfessorDisciplinaModel, UsuarioModel,
    EstadoTurmaModel, SolicitacaoAlteracaoModel, OfertaCursoModel)
from app.models import TurmaDisciplinaModel
from config import Config


class CourseApiTests(TestCase):
    @classmethod
    def setUpClass(cls):
        study.StudyTests.setUpClass.__func__(cls)

    setUp = study.StudyTests.setUp
    client = study.StudyTests.client
    post = study.StudyTests.post
    decide = study.StudyTests.decide

    def create(self, **fields):
        response = self.post('/api/cursos',{'disciplina_id':1,'titulo':'Curso MS04','descricao':'Estudo',**fields})
        self.assertEqual(response.status_code,201,response.text)
        return response.json['curso_id']

    def version(self,cid):
        response = self.client().get(f'/api/cursos/{cid}')
        self.assertEqual(response.status_code,200,response.text)
        return response.json['curso']['versao']

    def edit(self,cid,**fields):
        response = self.post(f'/api/cursos/{cid}/estrutura',{'versao':self.version(cid),**fields})
        self.assertEqual(response.status_code,200,response.text)
        return response.json

    def tree(self, *, text=True, count=2):
        cid = self.create()
        module = self.edit(cid,acao='adicionar',tipo='capitulo',titulo='Módulo 1')['item_id']
        chapter = self.edit(cid,acao='adicionar',tipo='tema',pai_id=module,titulo='Capítulo 1')['item_id']
        lessons = []
        for i in range(count):
            fields = {'tipo_aula':'texto','corpo':'Texto <script>fictício</script>'} if text else {'video':'abcdefghijk'}
            lessons.append(self.edit(cid,acao='adicionar',tipo='aula',pai_id=chapter,titulo=f'Aula {i+1}',**fields)['item_id'])
        return cid,module,chapter,lessons

    def publish(self,cid):
        response = self.post(f'/api/cursos/{cid}/solicitar-publicacao',{'versao':self.version(cid)})
        self.assertEqual(response.status_code,202,response.text)
        self.assertEqual(self.decide(response.json['id']).status_code,200)
        response = self.post(f'/api/cursos/{cid}/ofertas',{'versao':self.version(cid),'turma_disciplina_id':1},uid=1)
        self.assertEqual(response.status_code,200,response.text)
        return response.json['id']

    def upload(self,cid,aid, *, key=None, data=b'%PDF-1.4\nFicticio\n%%EOF'):
        return self.client().post(f'/api/cursos/{cid}/aulas/{aid}/recursos',data={
            'tipo':'arquivo','titulo':'Apostila','versao':str(self.version(cid)),
            'arquivo':(io.BytesIO(data),'apostila.pdf')},headers={
            'X-CSRF-Token':'study-csrf','Idempotency-Key':key or uuid4().hex})

    def test_teacher_draft_is_direct_private_and_legacy_policy_remains(self):
        cid = self.create()
        self.assertEqual(self.client(2).get(f'/api/cursos/{cid}').status_code,403)
        self.assertEqual(self.client(4).get(f'/api/cursos/{cid}').status_code,403)
        self.assertEqual(self.client(2).get('/api/cursos').json['ofertas'],[])
        response = self.post('/cursos',{'disciplina_id':1,'titulo':'Legado','descricao':''})
        self.assertEqual(response.status_code,202,response.text)
        with get_session() as db:
            self.assertEqual(db.query(CursoModel).count(),1)
        self.assertEqual(self.post(f'/cursos/{cid}/estrutura',{'acao':'curso','titulo':'Atalho'},uid=1).status_code,409)

    def test_full_tree_text_publication_offer_navigation_and_resume(self):
        cid,module,chapter,lessons = self.tree()
        self.assertEqual(self.client().get(f'/api/cursos/{cid}').json['modulos'][0]['capitulos'][0]['aulas'][1]['id'],lessons[1])
        offer = self.publish(cid)
        page = self.client(2).get(f'/api/aprender/{offer}')
        self.assertEqual(page.status_code,200,page.text)
        self.assertEqual(page.json['aula']['tipo'],'texto')
        self.assertIsNone(page.json['aula']['video_id'])
        self.assertEqual(page.json['proxima_id'],lessons[1])
        self.assertNotIn('corpo',page.json['modulos'][0]['capitulos'][0]['aulas'][0])
        opened = self.post(f'/api/aprender/{offer}/aulas/{lessons[1]}/abrir',{'versao':0},uid=2)
        self.assertEqual(opened.status_code,200,opened.text)
        resumed = self.client(2).get(f'/api/aprender/{offer}').json
        self.assertEqual(resumed['aula']['id'],lessons[1])
        self.assertEqual(resumed['progresso'],0)
        self.assertEqual(resumed['anterior_id'],lessons[0])
        self.assertIsNone(resumed['proxima_id'])
        self.assertEqual(self.client(2).get(f'/aprender/{offer}').status_code,200)

    def test_legacy_youtube_remains_valid(self):
        cid,module,chapter,lessons = self.tree(text=False,count=1)
        offer = self.publish(cid)
        self.assertEqual(self.client(2).get(f'/aprender/{offer}').status_code,200)
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}').json['aula']['video_id'],'abcdefghijk')

    def test_version_conflict_and_idempotent_edit(self):
        cid = self.create()
        data = {'acao':'curso','titulo':'Novo','descricao':'','versao':1}
        first = self.post(f'/api/cursos/{cid}/estrutura',data,key='edit')
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(self.post(f'/api/cursos/{cid}/estrutura',data,key='edit').json,first.json)
        self.assertEqual(self.post(f'/api/cursos/{cid}/estrutura',data).status_code,409)
        self.assertEqual(self.post(f'/api/cursos/{cid}/estrutura',{**data,'titulo':'Outro'},key='edit').status_code,409)
        self.assertEqual(self.version(cid),2)

    def test_missing_version_key_csrf_and_invalid_inputs(self):
        cid = self.create()
        path = f'/api/cursos/{cid}/estrutura'
        self.assertEqual(self.post(path,{'acao':'curso','titulo':'X'}).status_code,428)
        self.assertEqual(self.client().post(path,json={'versao':1}).status_code,403)
        self.assertEqual(self.client().post(path,json={'versao':1},headers={'X-CSRF-Token':'study-csrf'}).status_code,428)
        for version in (True,-1,'x','9'*100):
            self.assertEqual(self.post(path,{'acao':'curso','titulo':'X','versao':version}).status_code,400)
        self.assertEqual(self.post(path,{'acao':'curso','titulo':'X','versao':1,'professor_id':4}).status_code,400)
        self.assertEqual(self.version(cid),1)

    def test_other_course_parent_and_lesson_cannot_be_mutated(self):
        cid,module,chapter,lessons = self.tree()
        other = self.create()
        self.assertEqual(self.post(f'/api/cursos/{other}/estrutura',{'acao':'adicionar','tipo':'aula',
            'pai_id':chapter,'titulo':'Intrusão','video':'abcdefghijk','versao':1}).status_code,404)
        self.assertEqual(self.post(f'/api/cursos/{other}/estrutura',{'acao':'remover','tipo':'aula',
            'id':lessons[0],'versao':1}).status_code,404)
        self.assertEqual(self.version(other),1)

    def test_stale_publication_rejected_and_teacher_reviewer_cannot_publish(self):
        cid,module,chapter,lessons = self.tree()
        proposal = self.post(f'/api/cursos/{cid}/solicitar-publicacao',{'versao':self.version(cid)}).json['id']
        with get_session() as db:
            db.get(UsuarioModel,4).revisor_materiais = True
            db.commit()
        self.assertEqual(self.post(f'/solicitacoes/alteracoes/{proposal}/decidir',{'decisao':'aprovar'},uid=4).status_code,403)
        self.edit(cid,acao='curso',titulo='Mudou',descricao='')
        self.assertEqual(self.decide(proposal).status_code,409)
        self.assertEqual(self.client().get(f'/api/cursos/{cid}').json['curso']['estado'],'rascunho')

    def test_snapshot_rejects_changed_body_even_without_version_bump(self):
        cid,module,chapter,lessons = self.tree(count=1)
        proposal = self.post(f'/api/cursos/{cid}/solicitar-publicacao',{'versao':self.version(cid)}).json['id']
        with get_session() as db:
            db.get(AulaConteudoCursoModel,lessons[0]).corpo='Alteração externa'
            db.commit()
        self.assertEqual(self.decide(proposal).status_code,409)

    def test_revoked_author_blocks_review_and_edit(self):
        cid,module,chapter,lessons = self.tree(count=1)
        version = self.version(cid)
        proposal = self.post(f'/api/cursos/{cid}/solicitar-publicacao',{'versao':version}).json['id']
        with get_session() as db:
            db.query(ProfessorDisciplinaModel).filter_by(professor_id=1,disciplina_id=1).delete()
            db.commit()
        self.assertEqual(self.decide(proposal).status_code,403)
        self.assertEqual(self.post(f'/api/cursos/{cid}/estrutura',{'acao':'curso','titulo':'X','versao':version}).status_code,403)

    def test_empty_structure_and_invalid_lesson_are_rejected(self):
        cid = self.create()
        self.assertEqual(self.post(f'/api/cursos/{cid}/solicitar-publicacao',{'versao':1}).status_code,400)
        module = self.edit(cid,acao='adicionar',tipo='capitulo',titulo='Módulo')['item_id']
        chapter = self.edit(cid,acao='adicionar',tipo='tema',pai_id=module,titulo='Capítulo')['item_id']
        for values in ({'tipo_aula':'texto','corpo':''},{'tipo_aula':'texto','corpo':'Texto','video':'abcdefghijk'},
                {'tipo_aula':'video','video':'http://invalid.test/v'},{'tipo_aula':'script','corpo':'X'}):
            self.assertEqual(self.post(f'/api/cursos/{cid}/estrutura',{'acao':'adicionar','tipo':'aula','pai_id':chapter,
                'titulo':'Inválida','versao':self.version(cid),**values}).status_code,400)

    def test_reorder_remove_and_course_version(self):
        cid,module,chapter,lessons = self.tree()
        self.edit(cid,acao='subir',tipo='aula',id=lessons[1])
        ids = self.client().get(f'/api/cursos/{cid}').json['modulos'][0]['capitulos'][0]['aulas']
        self.assertEqual([r['id'] for r in ids],list(reversed(lessons)))
        self.edit(cid,acao='remover',tipo='aula',id=lessons[0])
        self.assertEqual(self.client().get(f'/api/cursos/{cid}/aulas/{lessons[0]}').status_code,404)

    def test_published_immutable_and_duplicate_preserves_content_without_progress(self):
        cid,module,chapter,lessons = self.tree(count=1)
        resource = self.upload(cid,lessons[0])
        self.assertEqual(resource.status_code,201,resource.text)
        offer = self.publish(cid)
        self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{lessons[0]}/concluir',{},uid=2).status_code,200)
        self.assertEqual(self.post(f'/api/cursos/{cid}/estrutura',{'acao':'curso','titulo':'X','versao':self.version(cid)}).status_code,409)
        copied = self.post(f'/api/cursos/{cid}/duplicar',{'versao':self.version(cid)})
        self.assertEqual(copied.status_code,201,copied.text)
        copyid = copied.json['curso_id']
        lesson = self.client().get(f'/api/cursos/{copyid}').json['modulos'][0]['capitulos'][0]['aulas'][0]['id']
        self.assertNotEqual(lesson,lessons[0])
        self.assertEqual(self.client().get(f'/api/cursos/{copyid}/aulas/{lesson}').json['tipo'],'texto')
        with get_session() as db:
            self.assertEqual(db.query(ProgressoAulaModel).count(),1)
            self.assertEqual(db.query(RetomadaCursoModel).count(),0)
            self.assertEqual(db.query(RecursoAulaCursoModel).count(),2)
        self.assertEqual(len(list(Path(self.fixture.folder.name).rglob('*.enc'))),1)
        copied_offer = self.publish(copyid)
        copied_resource = self.client().get(f'/api/cursos/{copyid}/aulas/{lesson}').json['recursos'][0]['id']
        self.assertNotEqual(copied_resource,resource.json['recurso']['id'])
        self.assertEqual(self.post(f'/api/cursos/{cid}/estado',{'estado':'arquivado','versao':self.version(cid)},uid=1).status_code,200)
        copied_page = self.client(2).get(f'/api/aprender/{copied_offer}')
        self.assertEqual(copied_page.status_code,200,copied_page.text)
        self.assertEqual(copied_page.json['progresso'],0)
        self.assertEqual(self.client(2).get(f'/api/aprender/{copied_offer}/aulas/{lesson}/recursos/{copied_resource}/arquivo').status_code,200)

    def test_student_requires_class_subject_active_account_and_offer(self):
        cid,module,chapter,lessons = self.tree(count=1)
        offer = self.publish(cid)
        self.assertEqual(self.client(5).get(f'/api/aprender/{offer}').status_code,404)
        with get_session() as db:
            db.query(AlunoDisciplinaModel).filter_by(aluno_id=1,disciplina_id=1).delete()
            db.commit()
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}').status_code,404)
        self.assertEqual(self.client(2).get(f'/aprender/{offer}').status_code,404)
        self.assertEqual(self.client(2).get('/api/cursos').json['ofertas'],[])

    def test_resume_is_separate_from_conclusion_and_idempotent(self):
        cid,module,chapter,lessons = self.tree()
        offer = self.publish(cid)
        opened = self.post(f'/api/aprender/{offer}/aulas/{lessons[1]}/abrir',{'versao':0},uid=2,key='open')
        self.assertEqual(opened.status_code,200,opened.text)
        self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{lessons[1]}/abrir',{'versao':0},uid=2,key='open').json,opened.json)
        self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{lessons[0]}/abrir',{'versao':0},uid=2).status_code,409)
        for _ in range(2):
            self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{lessons[1]}/concluir',{},uid=2).status_code,200)
        state = self.client(2).get(f'/api/aprender/{offer}').json
        self.assertEqual(state['aula']['id'],lessons[1])
        self.assertEqual(state['progresso'],50)
        with get_session() as db:
            self.assertEqual(db.query(ProgressoAulaModel).count(),1)

    def test_wrong_course_cannot_record_cursor_or_complete(self):
        cid,module,chapter,lessons = self.tree(count=1)
        offer = self.publish(cid)
        other,_,_,foreign = self.tree(count=1)
        for action,body in [('abrir',{'versao':0}),('concluir',{})]:
            self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{foreign[0]}/{action}',body,uid=2).status_code,404)
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}?aula={foreign[0]}').status_code,404)
        with get_session() as db:
            self.assertEqual(db.query(RetomadaCursoModel).count(),0)

    def test_no_javascript_form_open_redirects_without_marking_complete(self):
        cid,module,chapter,lessons = self.tree(count=1)
        offer = self.publish(cid)
        response = self.client(2).post(f'/api/aprender/{offer}/aulas/{lessons[0]}/abrir',data={
            'csrf_token':'study-csrf','idempotency_key':uuid4().hex,'versao':'0'})
        self.assertEqual(response.status_code,303,response.text)
        self.assertEqual(response.headers['Location'],f'/api/aprender/{offer}?aula={lessons[0]}')
        with get_session() as db:
            self.assertEqual(db.query(ProgressoAulaModel).count(),0)

    def test_file_encrypted_download_restricted_and_revocation_preserves_history(self):
        cid,module,chapter,lessons = self.tree(count=1)
        upload = self.upload(cid,lessons[0])
        self.assertEqual(upload.status_code,201,upload.text)
        rid = upload.json['recurso']['id']
        files = list(Path(self.fixture.folder.name).rglob('*.enc'))
        self.assertEqual(len(files),1)
        self.assertNotIn(b'%PDF',files[0].read_bytes())
        offer = self.publish(cid)
        url = f'/api/aprender/{offer}/aulas/{lessons[0]}/recursos/{rid}/arquivo'
        response = self.client(2).get(url)
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.data.startswith(b'%PDF'))
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
        self.assertIn('attachment',response.headers['Content-Disposition'])
        self.assertEqual(self.client(5).get(url).status_code,404)
        self.assertEqual(self.post(f'/api/cursos/{cid}/ofertas',{'versao':self.version(cid),
            'turma_disciplina_id':1,'ativa':False},uid=1).status_code,200)
        self.assertEqual(self.client(2).get(url).status_code,404)
        self.assertEqual(len(list(Path(self.fixture.folder.name).rglob('*.enc'))),1)

    def test_invalid_file_and_commit_failure_leave_no_orphans(self):
        cid,module,chapter,lessons = self.tree(count=1)
        for data in (b'<html>',b'%PDF-'+b'x'*(5*1024*1024)):
            self.assertEqual(self.upload(cid,lessons[0],data=data).status_code,400)
        before = self.version(cid)
        with patch('app.routes.cursos_api_routes.finish_submission',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.upload(cid,lessons[0])
        self.assertEqual(self.version(cid),before)
        self.assertEqual(list(Path(self.fixture.folder.name).rglob('*.enc')),[])
        with get_session() as db:
            self.assertEqual(db.query(RecursoAulaCursoModel).count(),0)

    def test_draft_file_review_requires_author_or_admin_and_replay_has_one_file(self):
        cid,module,chapter,lessons = self.tree(count=1)
        version = self.version(cid)
        url = f'/api/cursos/{cid}/aulas/{lessons[0]}/recursos'
        def upload():
            return self.client().post(url,data={'tipo':'arquivo','titulo':'Material','versao':str(version),
                'arquivo':(io.BytesIO(b'%PDF-1.4\nFicticio\n%%EOF'),'material.pdf')},
                headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':'same-file'})
        first = upload()
        self.assertEqual(first.status_code,201,first.text)
        self.assertEqual(upload().json,first.json)
        self.assertEqual(len(list(Path(self.fixture.folder.name).rglob('*.enc'))),1)
        rid = first.json['recurso']['id']
        for uid,status in ((3,200),(1,200),(2,403),(4,403)):
            response = self.client(uid).get(url+f'/{rid}/arquivo')
            self.assertEqual(response.status_code,status,response.text[:100])

    def test_distinct_offers_keep_independent_cursor_and_progress(self):
        cid,module,chapter,lessons = self.tree()
        first_offer = self.publish(cid)
        with get_session() as db:
            db.add(TurmaDisciplinaModel(id=3,turma_id=2,disciplina_id=1))
            db.add(AlunoTurmaModel(aluno_id=1,turma_id=2))
            db.commit()
        second = self.post(f'/api/cursos/{cid}/ofertas',{'turma_disciplina_id':3,'versao':self.version(cid)},uid=1)
        self.assertEqual(second.status_code,200,second.text)
        other_offer = second.json['id']
        self.assertEqual(self.post(f'/api/aprender/{first_offer}/aulas/{lessons[1]}/abrir',{'versao':0},uid=2).status_code,200)
        self.assertEqual(self.post(f'/api/aprender/{first_offer}/aulas/{lessons[1]}/concluir',{},uid=2).status_code,200)
        other = self.client(2).get(f'/api/aprender/{other_offer}').json
        self.assertEqual(other['retomada']['versao'],0)
        self.assertEqual(other['aula']['id'],lessons[0])
        self.assertEqual(other['progresso'],0)

    def test_archived_class_and_inactive_enrollment_revoke_access(self):
        cid,module,chapter,lessons = self.tree(count=1)
        offer = self.publish(cid)
        with get_session() as db:
            db.get(AlunoModel,1).status_matricula=' Trancada '
            db.commit()
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}').status_code,404)
        self.assertEqual(self.client(2).get('/api/cursos').json['ofertas'],[])
        with get_session() as db:
            db.get(AlunoModel,1).status_matricula='Ativo'
            db.add(EstadoTurmaModel(turma_id=1,arquivada=True))
            db.commit()
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}').status_code,404)
        self.assertEqual(self.client(2).get('/api/cursos').json['ofertas'],[])

    def test_legacy_pending_proposal_cannot_bypass_api_version_adoption(self):
        created = self.post('/cursos',{'disciplina_id':1,'professor_id':1,'titulo':'Legado','descricao':''},uid=1)
        self.assertEqual(created.status_code,201,created.text)
        cid = created.json['curso_id']
        proposal = self.post(f'/cursos/{cid}/estrutura',{'acao':'curso','titulo':'Título proposto','descricao':''})
        self.assertEqual(proposal.status_code,202,proposal.text)
        self.edit(cid,acao='curso',titulo='Legado',descricao='')
        self.assertEqual(self.decide(proposal.json['id']).status_code,409)

    def test_link_https_and_archive_resource_invalidates_snapshot(self):
        cid,module,chapter,lessons = self.tree(count=1)
        path = f'/api/cursos/{cid}/aulas/{lessons[0]}/recursos'
        for link in ('http://example.test','javascript:alert(1)','https://user:pw@example.test'):
            self.assertEqual(self.post(path,{'tipo':'link','titulo':'Link','link':link,'versao':self.version(cid)}).status_code,400)
        created = self.post(path,{'tipo':'link','titulo':'Link','link':'https://example.test/apoio','versao':self.version(cid)})
        self.assertEqual(created.status_code,201,created.text)
        rid = created.json['recurso']['id']
        proposal = self.post(f'/api/cursos/{cid}/solicitar-publicacao',{'versao':self.version(cid)}).json['id']
        self.assertEqual(self.post(path+f'/{rid}/arquivar',{'versao':self.version(cid)}).status_code,200)
        self.assertEqual(self.decide(proposal).status_code,409)

    def test_library_pagination_and_no_unbounded_response(self):
        with get_session() as db:
            db.add_all([CursoModel(disciplina_id=1,professor_id=1,titulo=f'Curso {i}') for i in range(26)])
            db.commit()
        first = self.client().get('/api/cursos').json
        second = self.client().get('/api/cursos?pagina=2').json
        self.assertEqual((first['total'],len(first['cursos']),len(second['cursos'])),(26,25,1))
        self.assertEqual(self.client().get('/api/cursos?pagina=0').status_code,400)

    def test_admin_can_publish_but_student_cannot_assign_offers(self):
        cid,module,chapter,lessons = self.tree(count=1)
        self.assertEqual(self.post(f'/api/cursos/{cid}/estado',{'estado':'publicado','versao':self.version(cid)}).status_code,403)
        response = self.post(f'/api/cursos/{cid}/estado',{'estado':'publicado','versao':self.version(cid)},uid=1)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.post(f'/api/cursos/{cid}/ofertas',{'turma_disciplina_id':1,'versao':self.version(cid)},uid=2).status_code,403)

    def test_missing_schema_fails_closed_without_startup_ddl(self):
        for model in (RecursoAulaCursoModel,RetomadaCursoModel,AulaConteudoCursoModel,CursoVersaoModel):
            model.__table__.drop(engine)
        statements = []
        def capture(conn,cursor,statement,parameters,context,many):
            statements.append(statement)
        event.listen(engine,'before_cursor_execute',capture)
        try:
            with patch.object(Config,'APP_ENV','production'):
                init_db()
            self.assertEqual(self.client().get('/api/cursos').status_code,503)
            self.assertEqual(self.client(1).get('/cursos').status_code,200)
        finally:
            event.remove(engine,'before_cursor_execute',capture)
        self.assertFalse(any(s.lstrip().upper().startswith(('CREATE','ALTER','DROP')) for s in statements))

    def test_authentication_and_inactive_account(self):
        self.assertEqual(self.app.test_client().get('/api/cursos').status_code,403)
        self.assertEqual(self.app.test_client().get('/api/cursos',headers={'Authorization':'Bearer invalid'}).status_code,401)
        client = self.client()
        with get_session() as db:
            db.get(UsuarioModel,3).estado='pendente'
            db.commit()
        self.assertEqual(client.get('/api/cursos').status_code,401)

    def test_discipline_context_is_authorized_and_old_revoke_cannot_bypass_version(self):
        cid,module,chapter,lessons = self.tree(count=1)
        offer = self.publish(cid)
        response = self.client(2).get('/api/estudos/disciplinas/1/cursos')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json['ofertas'][0]['id'],offer)
        self.assertEqual(self.client(5).get('/api/estudos/disciplinas/1/cursos').status_code,404)
        self.assertEqual(self.post(f'/cursos/ofertas/{offer}/revogar',{},uid=1).status_code,409)
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}').status_code,200)

    def test_all_completed_and_empty_legacy_course_are_safe(self):
        cid,module,chapter,lessons = self.tree()
        offer = self.publish(cid)
        for aid in lessons:
            self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{aid}/concluir',{},uid=2).status_code,200)
        state = self.client(2).get(f'/api/aprender/{offer}').json
        self.assertEqual(state['progresso'],100)
        self.assertEqual(state['aula']['id'],lessons[0])
        with get_session() as db:
            empty = CursoModel(disciplina_id=1,professor_id=1,titulo='Legado vazio',estado='publicado')
            db.add(empty)
            db.flush()
            row = OfertaCursoModel(curso_id=empty.id,turma_disciplina_id=1,ativa=True)
            db.add(row)
            db.commit()
            empty_offer = row.id
        response = self.client(2).get(f'/api/aprender/{empty_offer}')
        self.assertEqual(response.status_code,200,response.text)
        self.assertIsNone(response.json['aula'])
        self.assertEqual(response.json['progresso'],0)

    @skipUnless(engine.dialect.name=='mysql','Exige MySQL descartável')
    def test_concurrent_course_edits_have_one_effect(self):
        cid = self.create()
        barrier = threading.Barrier(2)
        def send(i):
            client = self.client()
            barrier.wait(timeout=20)
            return client.post(f'/api/cursos/{cid}/estrutura',json={'acao':'curso','titulo':f'Edicao {i}','versao':1},
                headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(send,range(2))),[200,409])

    @skipUnless(engine.dialect.name=='mysql','Exige MySQL descartável')
    def test_concurrent_resume_first_insert_is_versioned(self):
        cid,module,chapter,lessons = self.tree()
        offer = self.publish(cid)
        barrier = threading.Barrier(2)
        def send(aid):
            client = self.client(2)
            barrier.wait(timeout=20)
            return client.post(f'/api/aprender/{offer}/aulas/{aid}/abrir',json={'versao':0},
                headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(send,lessons)),[200,409])

    @skipUnless(engine.dialect.name=='mysql','Exige MySQL descartável')
    def test_concurrent_completion_has_one_persisted_result(self):
        cid,module,chapter,lessons = self.tree(count=1)
        offer = self.publish(cid)
        barrier = threading.Barrier(2)
        def send(i):
            client = self.client(2)
            barrier.wait(timeout=20)
            return client.post(f'/api/aprender/{offer}/aulas/{lessons[0]}/concluir',json={},
                headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(send,range(2))),[200,200])
        with get_session() as db:
            self.assertEqual(db.query(ProgressoAulaModel).count(),1)
