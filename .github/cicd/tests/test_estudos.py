"""Espaço da disciplina: banco descartável, autoria, revisão e arquivos privados."""
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4
from cryptography.fernet import Fernet
from sqlalchemy import event, inspect
import test_concurrency as fixtures
from config import Config
from app.database import engine, get_session, init_db
from app.models import (AlunoModel, AlunoDisciplinaModel, AlunoTurmaModel,
    ProfessorTurmaModel, TurmaModel, TurmaDisciplinaModel, DisciplinaModel, UsuarioModel,
    ConteudoEstudoModel, AuditoriaEstudoModel, AtribuicaoDocenteModel, EstadoTurmaModel,
    SolicitacaoAlteracaoModel, SecaoEstudoModel, ConteudoSecaoEstudoModel, AuditoriaSecaoEstudoModel)


class StudyTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        key = patch.object(Config,'DATA_ENCRYPTION_KEY',Fernet.generate_key().decode())
        key.start()
        self.addCleanup(key.stop)
        with get_session() as db:
            db.add(AlunoDisciplinaModel(aluno_id=1,disciplina_id=1))
            db.add(UsuarioModel(id=5,email='other-student@example.test',tipo='aluno',senha='unused'))
            db.add(TurmaModel(id=2,nome='Outra turma',codigo='T2',ano_letivo=2026))
            db.add(DisciplinaModel(id=2,nome='Outra matéria',codigo='D2',carga_horaria=40))
            db.flush()
            db.add(AlunoModel(id=2,usuario_id=5,nome='Outro aluno',matricula='A2'))
            db.add(TurmaDisciplinaModel(id=2,turma_id=2,disciplina_id=2))
            db.flush()
            db.add(AlunoTurmaModel(aluno_id=2,turma_id=2))
            db.add(AlunoDisciplinaModel(aluno_id=2,disciplina_id=2))
            db.commit()

    def client(self, uid=3):
        client = self.app.test_client()
        with get_session() as db:
            user = db.get(UsuarioModel,uid)
            with client.session_transaction() as state:
                state.update(user_id=uid,user_role=user.tipo,user_email=user.email,
                    auth_version=user.auth_version,csrf_token='study-csrf')
        return client

    def post(self, path, body, uid=3, key=None):
        return self.client(uid).post(path,json=body,headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':key or uuid4().hex})

    def create(self,uid=3,pair=1,**values):
        return self.post(f'/estudos/disciplinas/{pair}/novo',
            {'tipo':'aviso','titulo':'Aviso da disciplina','texto':'Leitura para a próxima aula',**values},uid)

    def upload(self,content=b'%PDF-1.4\nMaterial ficticio\n%%EOF',key=None,uid=3):
        return self.client(uid).post('/estudos/disciplinas/1/novo?formato=json',data={
            'tipo':'arquivo','titulo':'Apostila','texto':'Estude o primeiro capítulo.',
            'arquivo':(io.BytesIO(content),'material.pdf')},
            headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':key or uuid4().hex})

    def propose(self,rid,version=1,uid=3,key=None):
        return self.post(f'/estudos/conteudos/{rid}/publicar',{'versao':version},uid,key)

    def decide(self,rid,decision='aprovar'):
        return self.post(f'/solicitacoes/alteracoes/{rid}/decidir',{'decisao':decision},uid=1)

    def publish(self,rid):
        response = self.propose(rid)
        self.assertEqual(response.status_code,202,response.text)
        response = self.decide(response.json['id'])
        self.assertEqual(response.status_code,200,response.text)

    def test_draft_edit_review_and_publication_journey(self):
        created = self.create()
        self.assertEqual(created.status_code,201,created.text)
        rid = created.json['id']
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}').status_code,404)
        edited = self.post(f'/estudos/conteudos/{rid}/editar',{'titulo':'Aviso atualizado','texto':'Capítulo 2','versao':1})
        self.assertEqual(edited.status_code,200,edited.text)
        self.assertEqual(edited.json['versao'],2)
        proposal = self.propose(rid,version=2)
        self.assertEqual(proposal.status_code,202,proposal.text)
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}').status_code,404)
        self.assertIn('Conferir aviso ou material',self.client(1).get('/solicitacoes').text)
        self.assertEqual(self.decide(proposal.json['id']).status_code,200)
        page = self.client(2).get(f'/estudos/conteudos/{rid}')
        self.assertEqual(page.status_code,200,page.text)
        self.assertIn('Aviso atualizado',page.text)
        self.assertEqual(page.headers['Cache-Control'],'no-store')

    def test_rejection_and_stale_review_do_not_publish_changed_draft(self):
        rid = self.create().json['id']
        proposal = self.propose(rid).json['id']
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/editar',{'titulo':'Mudou','texto':'Outro texto','versao':1}).status_code,200)
        self.assertEqual(self.decide(proposal).status_code,409)
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}').status_code,404)
        self.assertEqual(self.decide(proposal,'rejeitar').status_code,200)
        second = self.propose(rid,version=2).json['id']
        self.assertEqual(self.decide(second,'rejeitar').status_code,200)
        with get_session() as db:
            self.assertEqual(db.get(ConteudoEstudoModel,rid).estado,'rascunho')

    def test_publication_replays_and_duplicate_pending_is_denied(self):
        rid = self.create().json['id']
        first = self.propose(rid,key='publish')
        self.assertEqual(self.propose(rid,key='publish').json,first.json)
        self.assertEqual(self.propose(rid).status_code,409)
        self.assertEqual(self.decide(first.json['id']).status_code,200)
        self.assertEqual(self.propose(rid,key='publish').json,first.json)
        with get_session() as db:
            self.assertEqual(db.query(SolicitacaoAlteracaoModel).filter_by(tipo='publicar_material').count(),1)

    def test_file_is_encrypted_scoped_and_idempotent(self):
        response = self.upload(key='upload')
        self.assertEqual(response.status_code,201,response.text)
        rid = response.json['id']
        self.assertEqual(self.upload(key='upload').json,response.json)
        files = list(Path(self.fixture.folder.name).rglob('*.enc'))
        self.assertEqual(len(files),1)
        self.assertNotIn(b'%PDF-',files[0].read_bytes())
        url = f'/estudos/conteudos/{rid}/arquivo'
        self.assertEqual(self.client(2).get(url).status_code,404)
        self.publish(rid)
        response = self.client(2).get(url)
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.data.startswith(b'%PDF-'))
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
        self.assertIn('attachment',response.headers['Content-Disposition'])
        self.assertEqual(self.client(5).get(url).status_code,404)
        self.assertEqual(self.app.test_client().get(url).status_code,403)
        self.assertEqual(self.client(2).get('/arquivos/download/'+files[0].name).status_code,404)

    def test_file_validation_and_transaction_failure_leave_no_file(self):
        for content in (b'<html>not a PDF</html>',b'%PDF-'+b'x'*(5*1024*1024)):
            self.assertEqual(self.upload(content).status_code,400)
        with patch('app.routes.estudo_routes.finish_submission',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.upload()
        self.assertEqual(list(Path(self.fixture.folder.name).rglob('*.enc')),[])
        with get_session() as db:
            self.assertEqual(db.query(ConteudoEstudoModel).count(),0)

    def test_links_are_https_and_text_is_escaped(self):
        for link in ('javascript:alert(1)','http://example.test/a','https://user:pass@example.test',
                'https://example.test/white space','https://example.test\\bad'):
            self.assertEqual(self.create(tipo='link',link=link).status_code,400)
        created = self.create(tipo='link',link='https://example.test/material?a=1&b=2',titulo='<script>alert(1)</script>')
        self.assertEqual(created.status_code,201,created.text)
        self.publish(created.json['id'])
        page = self.client(2).get(f"/estudos/conteudos/{created.json['id']}")
        self.assertIn('&lt;script&gt;',page.text)
        self.assertNotIn('<script>alert(1)</script>',page.text)
        self.assertIn('rel="noopener noreferrer"',page.text)

    def test_student_requires_both_class_and_subject_enrollment(self):
        rid = self.create().json['id']
        self.publish(rid)
        with get_session() as db:
            db.query(AlunoDisciplinaModel).filter_by(aluno_id=1,disciplina_id=1).delete()
            db.commit()
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}').status_code,404)
        self.assertEqual(self.client(2).get('/estudos?formato=json').json['disciplinas'],[])
        self.assertEqual(self.create(uid=2).status_code,403)
        self.assertEqual(self.client(5).get('/estudos/disciplinas/1').status_code,404)

    def test_revoked_or_managed_assignment_does_not_fall_back_to_legacy_pairs(self):
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=1,arquivada=False))
            db.commit()
        self.assertEqual(self.create().status_code,404)
        with get_session() as db:
            db.add(AtribuicaoDocenteModel(professor_id=1,turma_disciplina_id=1,ativo=True))
            db.commit()
        rid = self.create().json['id']
        proposal = self.propose(rid).json['id']
        with get_session() as db:
            db.query(AtribuicaoDocenteModel).update({'ativo':False})
            db.commit()
        self.assertEqual(self.decide(proposal).status_code,404)
        self.assertEqual(self.client().get(f'/estudos/conteudos/{rid}').status_code,404)

    def test_other_teacher_cannot_edit_or_publish_authors_draft(self):
        rid = self.create().json['id']
        with get_session() as db:
            db.add(ProfessorTurmaModel(professor_id=2,turma_id=1))
            db.commit()
        self.assertEqual(self.client(4).get(f'/estudos/conteudos/{rid}').status_code,404)
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/editar',{'titulo':'Mudança','texto':'Teste','versao':1},uid=4).status_code,403)
        self.assertEqual(self.propose(rid,uid=4).status_code,403)

    def test_archiving_revokes_student_access_and_preserves_file_and_audit(self):
        rid = self.upload().json['id']
        self.publish(rid)
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/arquivar',{'versao':1}).status_code,409)
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/arquivar',{'versao':2}).status_code,200)
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}/arquivo').status_code,404)
        self.assertEqual(len(list(Path(self.fixture.folder.name).rglob('*.enc'))),1)
        with get_session() as db:
            self.assertEqual(db.get(ConteudoEstudoModel,rid).estado,'arquivado')
            self.assertEqual(db.query(AuditoriaEstudoModel).filter_by(acao='arquivar').count(),1)

    def test_published_content_is_immutable_and_inactive_account_is_denied(self):
        rid = self.create().json['id']
        self.publish(rid)
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/editar',{'titulo':'Mudou','texto':'Teste','versao':2}).status_code,409)
        client = self.client()
        with get_session() as db:
            db.get(UsuarioModel,3).estado='pendente'
            db.commit()
        self.assertEqual(client.get('/estudos').status_code,401)

    def test_validation_errors_and_csrf_do_not_change_persisted_draft(self):
        rid = self.create().json['id']
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/editar',{'titulo':'Novo','texto':'Texto','versao':9}).status_code,409)
        self.assertEqual(self.post(f'/estudos/conteudos/{rid}/editar',{'titulo':'','texto':'Texto','versao':1}).status_code,400)
        self.assertEqual(self.client().post('/estudos/disciplinas/1/novo',data={'tipo':'aviso'}).status_code,403)
        with get_session() as db:
            self.assertEqual(db.get(ConteudoEstudoModel,rid).titulo,'Aviso da disciplina')
            self.assertEqual(db.get(ConteudoEstudoModel,rid).versao,1)

    def test_content_is_paginated_and_drafts_are_not_in_student_list(self):
        with get_session() as db:
            db.add_all([ConteudoEstudoModel(turma_disciplina_id=1,autor_id=3,tipo='aviso',titulo=f'Aviso {i}',texto='Texto',estado='publicado') for i in range(26)])
            db.add(ConteudoEstudoModel(turma_disciplina_id=1,autor_id=3,tipo='aviso',titulo='Rascunho privado',texto='Texto'))
            db.commit()
        first = self.client(2).get('/estudos/disciplinas/1?formato=json').json
        second = self.client(2).get('/estudos/disciplinas/1?formato=json&pagina=2').json
        self.assertEqual((first['total'],len(first['conteudos']),len(second['conteudos'])),(26,25,1))
        self.assertTrue(all(r['estado']=='publicado' for r in first['conteudos']))

    def test_missing_optional_schema_is_503_and_startup_does_not_apply_ddl(self):
        # Drop dependent MS03 tables first, including on strict MySQL FK checks.
        for model in (AuditoriaSecaoEstudoModel,ConteudoSecaoEstudoModel,SecaoEstudoModel):
            model.__table__.drop(engine)
        AuditoriaEstudoModel.__table__.drop(engine)
        ConteudoEstudoModel.__table__.drop(engine)
        before = inspect(engine).get_table_names()
        statements=[]
        def capture(conn,cursor,statement,parameters,context,many):
            statements.append(statement)
        event.listen(engine,'before_cursor_execute',capture)
        try:
            with patch.object(Config,'APP_ENV','production'):
                init_db()
            self.assertEqual(self.client().get('/estudos?formato=json').status_code,503)
            self.assertEqual(self.post('/solicitacoes/alteracoes',{'tipo':'publicar_material',
                'payload':{'conteudo_id':1,'versao':1}}).status_code,503)
            self.assertEqual(self.client(1).get('/admin/dashboard').status_code,200)
        finally:
            event.remove(engine,'before_cursor_execute',capture)
        self.assertEqual(before,inspect(engine).get_table_names())
        self.assertFalse(any(s.lstrip().upper().startswith(('CREATE','ALTER','DROP')) for s in statements))

    def test_admin_can_publish_directly_but_student_cannot(self):
        rid=self.create().json['id']
        self.assertEqual(self.propose(rid,uid=2).status_code,403)
        published=self.propose(rid,uid=1,key='admin-publish')
        self.assertEqual(published.status_code,200,published.text)
        self.assertEqual(self.propose(rid,uid=1,key='admin-publish').json,published.json)
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}').status_code,200)

    def test_creation_key_is_scoped_to_offer(self):
        body={'tipo':'aviso','titulo':'Mesmo texto','texto':'Material de estudo'}
        a=self.post('/estudos/disciplinas/1/novo',body,uid=1,key='same-key')
        b=self.post('/estudos/disciplinas/2/novo',body,uid=1,key='same-key')
        self.assertEqual((a.status_code,b.status_code),(201,201))
        self.assertNotEqual(a.json['id'],b.json['id'])

    def test_archived_class_and_inactive_enrollment_revoke_access(self):
        rid=self.create().json['id']
        self.publish(rid)
        with get_session() as db:
            db.get(AlunoModel,1).status_matricula='Trancada'
            db.commit()
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}').status_code,404)
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=1,arquivada=True))
            db.commit()
        self.assertEqual(self.create().status_code,404)

    def test_database_rejects_incomplete_file_metadata(self):
        from sqlalchemy.exc import IntegrityError, OperationalError
        with get_session() as db:
            db.add(ConteudoEstudoModel(turma_disciplina_id=1,autor_id=3,tipo='arquivo',
                titulo='Inválido',arquivo='a'*32+'.enc',mime='application/pdf',tamanho=None))
            # PyMySQL classifies CHECK error 3819 as OperationalError; SQLite
            # uses IntegrityError. Require the specific constraint in both.
            with self.assertRaises((IntegrityError,OperationalError)) as rejected:
                db.flush()
            self.assertIn('ck_estudo_recurso',str(rejected.exception.orig))
            if engine.dialect.name == 'mysql':
                self.assertEqual(rejected.exception.orig.args[0],3819)
            else:
                self.assertIsInstance(rejected.exception,IntegrityError)
            db.rollback()
            self.assertEqual(db.query(ConteudoEstudoModel).count(),0)

    @skipUnless(engine.dialect.name=='mysql','Concorrência exige MySQL descartável')
    def test_concurrent_draft_edits_have_one_effect(self):
        rid=self.create().json['id']
        barrier=threading.Barrier(2)
        def edit(i):
            client=self.client()
            barrier.wait(timeout=15)
            return client.post(f'/estudos/conteudos/{rid}/editar',json={'versao':1,'titulo':f'Edição {i}','texto':'Texto'},
                headers={'X-CSRF-Token':'study-csrf','Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(edit,range(2))),[200,409])
