"""MS03: autoria de abas e revogação de conteúdo em banco descartável."""
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
from app.models import (SecaoEstudoModel, ConteudoSecaoEstudoModel, AuditoriaSecaoEstudoModel,
    ConteudoEstudoModel, ProfessorTurmaModel, AtribuicaoDocenteModel, EstadoTurmaModel)
from config import Config


class SectionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        study.StudyTests.setUpClass.__func__(cls)

    setUp = study.StudyTests.setUp
    client = study.StudyTests.client
    post = study.StudyTests.post
    create = study.StudyTests.create
    propose = study.StudyTests.propose
    decide = study.StudyTests.decide
    publish = study.StudyTests.publish

    def section(self,uid=3,pair=1,key=None,**values):
        return self.post(f'/estudos/disciplinas/{pair}/abas',{'nome':'Capítulo 1','ordem':10,**values},uid,key)

    def test_create_rename_order_and_replay_preserve_audited_versions(self):
        first = self.section(key='new-section')
        self.assertEqual(first.status_code,201,first.text)
        self.assertEqual(self.section(key='new-section').json,first.json)
        sid = first.json['id']
        second = self.section(nome='Introdução',ordem=0).json['id']
        url = f'/estudos/abas/{sid}/editar'
        payload = {'nome':'Exercícios','ordem':0,'versao':1}
        changed = self.post(url,payload,key='rename')
        self.assertEqual(changed.status_code,200,changed.text)
        self.assertEqual(self.post(url,payload,key='rename').json,changed.json)
        self.assertEqual(self.post(url,payload).status_code,409)
        tabs = self.client(2).get('/estudos/disciplinas/1?formato=json').json['abas']
        self.assertEqual([r['id'] for r in tabs],[sid,second])
        self.assertEqual(tabs[0]['nome'],'Exercícios')
        with get_session() as db:
            audit = db.query(AuditoriaSecaoEstudoModel).filter_by(secao_id=sid).order_by(AuditoriaSecaoEstudoModel.id).all()
            self.assertEqual([(r.nome,r.ordem,r.versao) for r in audit],[('Capítulo 1',10,1),('Exercícios',0,2)])

    def test_student_other_teacher_and_foreign_offer_cannot_mutate(self):
        sid = self.section().json['id']
        self.assertEqual(self.section(uid=2).status_code,403)
        self.assertEqual(self.section(uid=3,pair=2).status_code,404)
        with get_session() as db:
            db.add(ProfessorTurmaModel(professor_id=2,turma_id=1))
            db.commit()
        for action,body in [('editar',{'nome':'Intrusão','ordem':0,'versao':1}),('arquivar',{'versao':1})]:
            for uid in (2,4):
                self.assertEqual(self.post(f'/estudos/abas/{sid}/{action}',body,uid).status_code,403)
        self.assertEqual(self.create(uid=4,secao_id=sid).status_code,403)
        self.assertEqual(self.create(uid=1,pair=2,secao_id=sid).status_code,400)
        self.assertEqual(self.client(1).get(f'/estudos/disciplinas/2?aba=secao-{sid}').status_code,404)
        self.assertEqual(self.client(5).get(f'/estudos/disciplinas/1?aba=secao-{sid}').status_code,404)

    def test_custom_tab_does_not_publish_drafts_and_fixed_tabs_are_preserved(self):
        sid = self.section().json['id']
        rid = self.create(secao_id=sid).json['id']
        standard = self.create(titulo='Aviso geral').json['id']
        tab = f'/estudos/disciplinas/1?aba=secao-{sid}&formato=json'
        self.assertEqual(self.client(2).get(tab).json['conteudos'],[])
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}').status_code,404)
        self.publish(rid)
        self.publish(standard)
        self.assertEqual([r['id'] for r in self.client(2).get(tab).json['conteudos']],[rid])
        self.assertEqual([r['id'] for r in self.client(2).get('/estudos/disciplinas/1?formato=json').json['conteudos']],[standard])

    def test_archiving_revokes_direct_access_and_download_without_deleting(self):
        sid = self.section().json['id']
        response = self.client().post('/estudos/disciplinas/1/novo?formato=json',data={
            'tipo':'arquivo','titulo':'Material da aba','secao_id':str(sid),
            'arquivo':(io.BytesIO(b'%PDF-1.4\nFicticio\n%%EOF'),'material.pdf')},
            headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':uuid4().hex})
        self.assertEqual(response.status_code,201,response.text)
        rid = response.json['id']
        self.publish(rid)
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}/arquivo').status_code,200)
        url = f'/estudos/abas/{sid}/arquivar'
        archived = self.post(url,{'versao':1},key='archive')
        self.assertEqual(archived.status_code,200,archived.text)
        self.assertEqual(self.post(url,{'versao':1},key='archive').json,archived.json)
        for suffix in ('','/arquivo'):
            self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}'+suffix).status_code,404)
        self.assertEqual(self.client(2).get(f'/estudos/disciplinas/1?aba=secao-{sid}').status_code,404)
        self.assertEqual(self.client(2).get('/estudos/disciplinas/1?formato=json').json['abas'],[])
        self.assertEqual(self.client().get(f'/estudos/conteudos/{rid}').status_code,200)
        self.assertEqual(len(list(Path(self.fixture.folder.name).rglob('*.enc'))),1)
        with get_session() as db:
            self.assertEqual(db.get(ConteudoEstudoModel,rid).estado,'publicado')
            self.assertEqual(db.get(ConteudoSecaoEstudoModel,rid).secao_id,sid)
            self.assertEqual(db.query(AuditoriaSecaoEstudoModel).filter_by(secao_id=sid,acao='arquivar').count(),1)

    def test_archived_section_blocks_pending_and_direct_publication(self):
        sid = self.section().json['id']
        rid = self.create(secao_id=sid).json['id']
        proposal = self.propose(rid).json['id']
        self.assertEqual(self.post(f'/estudos/abas/{sid}/arquivar',{'versao':1}).status_code,200)
        self.assertEqual(self.decide(proposal).status_code,404)
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/publicar',{'versao':1},uid=1).status_code,404)
        self.assertEqual(self.create(secao_id=sid).status_code,404)

    def test_validation_csrf_and_failed_commit_leave_state_unchanged(self):
        for values in ({'nome':''},{'nome':'x'*81},{'ordem':-1},{'ordem':1.5},{'ordem':True},{'ordem':'9'*5000}):
            self.assertEqual(self.section(**values).status_code,400)
        self.assertEqual(self.client().post('/estudos/disciplinas/1/abas',json={'nome':'Outra'}).status_code,403)
        sid = self.section().json['id']
        self.assertEqual(self.post(f'/estudos/abas/{sid}/editar',{'nome':'Outra','ordem':0}).status_code,428)
        with patch('app.routes.estudo_routes.finish_submission',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.post(f'/estudos/abas/{sid}/arquivar',{'versao':1})
        with get_session() as db:
            self.assertEqual(db.get(SecaoEstudoModel,sid).estado,'ativa')
            self.assertEqual(db.get(SecaoEstudoModel,sid).versao,1)
            self.assertEqual(db.query(AuditoriaSecaoEstudoModel).count(),1)

    def test_escaped_names_and_admin_can_organize(self):
        sid = self.section(nome='<script>bad()</script>').json['id']
        page = self.client().get('/estudos/disciplinas/1/abas')
        self.assertEqual(page.status_code,200,page.text)
        self.assertIn('&lt;script&gt;',page.text)
        self.assertNotIn('<script>bad()</script>',page.text)
        self.assertEqual(self.post(f'/estudos/abas/{sid}/editar',{'nome':'Aba revisada','ordem':5,'versao':1},uid=1).status_code,200)

    def test_revoked_assignment_blocks_section_mutation(self):
        sid = self.section().json['id']
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=1,arquivada=False))
            db.add(AtribuicaoDocenteModel(turma_disciplina_id=1,professor_id=1,ativo=False))
            db.commit()
        self.assertEqual(self.post(f'/estudos/abas/{sid}/arquivar',{'versao':1}).status_code,404)

    def test_missing_section_schema_preserves_ms02_without_startup_ddl(self):
        for model in (AuditoriaSecaoEstudoModel,ConteudoSecaoEstudoModel,SecaoEstudoModel):
            model.__table__.drop(engine)
        before = inspect(engine).get_table_names()
        statements = []
        def capture(conn,cursor,statement,parameters,context,many):
            statements.append(statement)
        event.listen(engine,'before_cursor_execute',capture)
        try:
            with patch.object(Config,'APP_ENV','production'):
                init_db()
            self.assertEqual(self.client().get('/estudos/disciplinas/1').status_code,200)
            self.assertEqual(self.create().status_code,201)
            self.assertEqual(self.section().status_code,503)
        finally:
            event.remove(engine,'before_cursor_execute',capture)
        self.assertEqual(before,inspect(engine).get_table_names())
        self.assertFalse(any(s.lstrip().upper().startswith(('CREATE','ALTER','DROP')) for s in statements))

    def test_partial_section_schema_fails_closed(self):
        AuditoriaSecaoEstudoModel.__table__.drop(engine)
        self.assertEqual(self.client(2).get('/estudos/disciplinas/1').status_code,503)
        self.assertEqual(self.section().status_code,503)

    @skipUnless(engine.dialect.name=='mysql','Concorrência exige MySQL descartável')
    def test_concurrent_rename_and_archive_have_one_effect(self):
        sid = self.section().json['id']
        barrier = threading.Barrier(2)
        def send(action):
            client = self.client()
            barrier.wait(timeout=15)
            return client.post(f'/estudos/abas/{sid}/{action}',json={'nome':'Novo','ordem':0,'versao':1},
                headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(send,['editar','arquivar'])),[200,409])
