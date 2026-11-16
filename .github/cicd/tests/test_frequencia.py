"""Frequência em banco descartável; nunca executar contra bancos das escolas."""
import io
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from datetime import date
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash
from cryptography.fernet import Fernet
from config import Config
from app import create_app
from app.database import Base, engine, get_session
from app.models import (UsuarioModel, AlunoModel, ProfessorModel, TurmaModel, DisciplinaModel,
                        TurmaDisciplinaModel, AlunoTurmaModel, ProfessorTurmaModel, ProfessorDisciplinaModel)
from app.models.frequencia_model import ChamadaModel, PresencaModel, AtestadoModel
from app.models.curso_model import AtribuicaoDocenteModel, EstadoTurmaModel


class FrequenciaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv('EDUFAST_TEST_DISPOSABLE') != '1':
            raise RuntimeError('Use somente o executor de testes descartáveis.')
        cls.app = create_app()
        old_key = Config.DATA_ENCRYPTION_KEY
        Config.DATA_ENCRYPTION_KEY = Fernet.generate_key().decode('ascii')
        cls.addClassCleanup(setattr, Config, 'DATA_ENCRYPTION_KEY', old_key)
        cls.app.config['TESTING'] = True
        cls.password = generate_password_hash('synthetic-password')

    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app.config['UPLOAD_FOLDER'] = self.folder.name
        self.day = date.today().isoformat()
        with get_session() as db:
            for uid, role in [(1,'admin'),(2,'professor'),(3,'professor'),(4,'aluno'),(5,'aluno'),(6,'aluno')]:
                db.add(UsuarioModel(id=uid, email=f'u{uid}@example.test', senha=self.password, tipo=role))
            db.flush()
            db.add_all([TurmaModel(id=i, codigo=f'T{i}', nome=f'Turma {i}', ano_letivo=2026) for i in (1,2)])
            db.add_all([DisciplinaModel(id=i, codigo=f'D{i}', nome=f'Matéria {i}', carga_horaria=60) for i in (1,2)])
            db.add_all([ProfessorModel(id=i, usuario_id=i+1, nome=f'Professor {i}', cpf=f'TESTE-P{i}') for i in (1,2)])
            db.add_all([AlunoModel(id=i, usuario_id=i+3, nome=f'Aluno {i}', matricula=f'A{i}') for i in (1,2,3)])
            db.flush()
            db.add_all([TurmaDisciplinaModel(id=i, turma_id=i, disciplina_id=i) for i in (1,2)])
            db.add_all([ProfessorTurmaModel(professor_id=i,turma_id=i) for i in (1,2)])
            db.add_all([ProfessorDisciplinaModel(professor_id=i,disciplina_id=i) for i in (1,2)])
            db.add_all([AlunoTurmaModel(aluno_id=i,turma_id=1 if i<3 else 2) for i in (1,2,3)])
            db.commit()
        self.clients, self.tokens = {}, {}
        for uid in range(1,7):
            client = self.app.test_client()
            response = client.post('/login', json={'email':f'u{uid}@example.test','senha':'synthetic-password'})
            self.assertEqual(response.status_code, 200)
            self.clients[uid], self.tokens[uid] = client, response.json['token']

    def post(self, uid, url, data, key=None):
        return self.clients[uid].post(url, json=data, headers={
            'Authorization':'Bearer '+self.tokens[uid], 'Idempotency-Key':key or uuid4().hex})

    def proposal(self, uid=2, **overrides):
        data = {'turma_disciplina_id':1, 'dia':self.day,'aula':1,'presencas':{'1':'presente','2':'falta'}}
        data.update(overrides)
        return self.post(uid, '/frequencia/chamadas', data)

    def decision(self, kind, rid, decision='aprovar', version=1, uid=1):
        return self.post(uid, f'/frequencia/{kind}/{rid}/decidir',
            {'decisao':decision,'versao':version,'motivo':'Conferência administrativa'})

    def legacy_pending(self, **overrides):
        """Fixture representing a pending call created before direct confirmation."""
        response = self.proposal(**overrides)
        self.assertEqual(response.status_code, 201, response.text)
        with get_session() as db:
            row = db.get(ChamadaModel, response.json['id'])
            row.estado, row.decidido_por = 'pendente', None
            if row.anterior_id:
                db.get(ChamadaModel, row.anterior_id).estado = 'aprovada'
            db.commit()
        return response

    def report(self, uid=1, **extra):
        return self.clients[uid].get('/frequencia/relatorio', query_string={
            'inicio':self.day,'fim':self.day,'formato':'json',**extra})

    def certificate(self, uid=5, sid='2', key=None):
        return self.clients[uid].post('/frequencia/atestados?formato=json', data={
            'aluno_id':sid,'inicio':self.day,'fim':self.day,
            'arquivo':(io.BytesIO(b'%PDF-1.4\nDocumento ficticio\n%%EOF'), 'teste.pdf')},
            headers={'Authorization':'Bearer '+self.tokens[uid], 'Idempotency-Key':key or uuid4().hex})

    def test_teacher_confirms_and_report_is_available_without_admin_decision(self):
        proposed = self.proposal()
        self.assertEqual(proposed.status_code, 201)
        self.assertEqual(proposed.json['estado'], 'aprovada')
        self.assertEqual(proposed.json['versao'], 1)
        self.assertEqual(self.decision('chamada', proposed.json['id'],uid=2).status_code, 403)
        self.assertEqual(self.decision('chamada', proposed.json['id']).status_code, 409)
        result = self.report().json['totais']
        self.assertEqual([(r['presentes'],r['faltas']) for r in result], [(1,0),(0,1)])
        with get_session() as db:
            from app.models.frequencia_model import AuditoriaFrequenciaModel
            self.assertEqual(db.get(ChamadaModel, proposed.json['id']).decidido_por, 2)
            self.assertEqual(db.query(AuditoriaFrequenciaModel).filter_by(acao='confirmar_chamada', ator_id=2).count(), 1)

    def test_outside_scope_incomplete_roster_and_future_are_denied(self):
        self.assertEqual(self.proposal(uid=3).status_code, 403)
        self.assertEqual(self.proposal(uid=4).status_code, 403)
        self.assertEqual(self.proposal(presencas={'1':'presente'}).status_code, 400)
        self.assertEqual(self.proposal(presencas={'1':'presente','3':'falta'}).status_code, 400)
        self.assertEqual(self.proposal(presencas={'1':'justificada','2':'presente'}).status_code, 400)
        self.assertEqual(self.proposal(dia='2999-01-01').status_code, 400)
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),0)

    def test_replay_is_exact_and_duplicate_lesson_is_rejected(self):
        body = {'turma_disciplina_id':1,'dia':self.day,'aula':1,'presencas':{'1':'presente','2':'falta'}}
        a = self.post(2,'/frequencia/chamadas',body,key='same')
        b = self.post(2,'/frequencia/chamadas',body,key='same')
        self.assertEqual(a.json,b.json)
        self.assertEqual(self.proposal().status_code,409)
        body['aula']=2
        self.assertEqual(self.post(2,'/frequencia/chamadas',body,key='same').status_code,409)
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),1)
            self.assertEqual(db.query(PresencaModel).count(),2)

    def test_correction_is_immediate_and_preserves_original_history(self):
        first = self.proposal().json['id']
        correction = self.proposal(anterior_id=first,versao=1,motivo='Corrigir marcação',presencas={'1':'presente','2':'presente'})
        self.assertEqual(correction.status_code,201)
        totals = self.report().json['totais']
        self.assertEqual([r['presentes'] for r in totals],[1,1])
        with get_session() as db:
            self.assertEqual(db.get(ChamadaModel,first).estado,'substituida')
            self.assertEqual(db.get(ChamadaModel,correction.json['id']).anterior_id,first)
            self.assertEqual(db.query(PresencaModel).filter_by(chamada_id=first,aluno_id=2).one().situacao,'falta')

    def test_rejected_correction_does_not_replace_approved(self):
        first = self.proposal().json['id']
        correction = self.legacy_pending(anterior_id=first,versao=1,motivo='Revisar marcação').json['id']
        self.decision('chamada',correction,decision='rejeitar')
        self.assertEqual(self.report().json['totais'][1]['faltas'],1)

    def test_correction_requires_current_reference_version_and_reason(self):
        first = self.proposal().json['id']
        for fields, status in [({},409), ({'anterior_id':first},428),
                ({'anterior_id':first,'versao':9},409),
                ({'anterior_id':first,'versao':1},400)]:
            self.assertEqual(self.proposal(**fields).status_code,status)
        body = {'anterior_id':first,'versao':1,'motivo':'Correção conferida',
                'presencas':{'1':'presente','2':'presente'}}
        correction = self.proposal(**body)
        self.assertEqual(correction.status_code,201,correction.text)
        self.assertEqual(self.proposal(**body).status_code,409)
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),2)
            self.assertEqual(db.query(ChamadaModel).filter_by(estado='aprovada').count(),1)

    def test_correction_uses_original_roster_and_form_is_scoped(self):
        first = self.proposal().json['id']
        with get_session() as db:
            db.query(AlunoTurmaModel).filter_by(aluno_id=2,turma_id=1).delete()
            db.commit()
        url = f'/frequencia/turmas/1/chamada?chamada_id={first}'
        page = self.clients[2].get(url)
        self.assertEqual(page.status_code,200)
        self.assertIn('name="aluno_2"',page.text)
        self.assertIn('name="anterior_id"',page.text)
        self.assertEqual(self.clients[3].get(url).status_code,403)
        self.assertEqual(self.clients[2].get(f'/frequencia/turmas/1/chamada?chamada_id=999').status_code,404)
        corrected = self.proposal(anterior_id=first,versao=1,motivo='Revisar elenco original')
        self.assertEqual(corrected.status_code,201,corrected.text)
        self.assertEqual(self.clients[2].get(url).status_code,409)

    def test_legacy_pending_is_preserved_and_blocks_new_call_until_decision(self):
        rid = self.legacy_pending().json['id']
        self.assertEqual(self.report().json['totais'],[])
        self.assertEqual(self.proposal().status_code,409)
        with get_session() as db:
            self.assertEqual(db.get(ChamadaModel,rid).estado,'pendente')
        self.assertEqual(self.decision('chamada',rid).status_code,200)
        self.assertEqual(len(self.report().json['totais']),2)

    def test_failed_correction_rolls_back_replacement_and_marks(self):
        rid = self.proposal().json['id']
        with patch('app.routes.frequencia_routes.finish_submission',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.proposal(anterior_id=rid,versao=1,motivo='Correção interrompida')
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),1)
            self.assertEqual(db.get(ChamadaModel,rid).estado,'aprovada')
            self.assertEqual(db.get(ChamadaModel,rid).versao,1)

    def test_archived_class_blocks_direct_confirmation(self):
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=1,arquivada=True))
            db.commit()
        self.assertEqual(self.proposal().status_code,409)
        self.assertEqual(self.clients[2].get('/frequencia/turmas/1/chamada').status_code,409)

    def test_correction_replay_does_not_duplicate_history(self):
        first = self.proposal().json['id']
        data = {'turma_disciplina_id':1,'dia':self.day,'aula':1,'anterior_id':first,
                'versao':1,'motivo':'Revisão idempotente','presencas':{'1':'presente','2':'presente'}}
        a = self.post(2,'/frequencia/chamadas',data,key='correction')
        b = self.post(2,'/frequencia/chamadas',data,key='correction')
        self.assertEqual(a.status_code,201)
        self.assertEqual(a.json,b.json)
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),2)

    def test_version_and_revoked_assignment_block_approval(self):
        rid = self.legacy_pending().json['id']
        self.assertEqual(self.decision('chamada',rid,version=9).status_code,409)
        with get_session() as db:
            db.query(ProfessorTurmaModel).filter_by(professor_id=1).delete()
            db.commit()
        self.assertEqual(self.decision('chamada',rid).status_code,403)
        self.assertEqual(self.report().json['totais'],[])

    def test_accepted_certificate_justifies_but_does_not_remove_absence(self):
        self.proposal()
        certificate = self.certificate()
        self.assertEqual(certificate.status_code,201)
        self.assertEqual(self.report().json['totais'][1]['justificadas'],0)
        self.assertEqual(self.decision('atestado',certificate.json['id']).status_code,200)
        row = self.report().json['totais'][1]
        self.assertEqual((row['justificadas'],row['faltas_total'],row['percentual_presenca']),(1,1,'0.00'))
        with get_session() as db:
            self.assertEqual(db.query(PresencaModel).filter_by(aluno_id=2).one().situacao,'falta')

    def test_certificate_is_private_encrypted_and_replay_does_not_duplicate_file(self):
        certificate = self.certificate(key='cert')
        rid = certificate.json['id']
        self.assertEqual(self.certificate(key='cert').json,certificate.json)
        files = list(Path(self.folder.name).rglob('*.enc'))
        self.assertEqual(len(files),1)
        self.assertNotIn(b'%PDF-',files[0].read_bytes())
        url = f'/frequencia/atestados/{rid}/arquivo'
        self.assertEqual(self.clients[5].get(url).status_code,200)
        self.assertEqual(self.clients[1].get(url).status_code,200)
        self.assertEqual(self.clients[2].get(url).status_code,404)
        self.assertEqual(self.clients[4].get(url).status_code,404)
        self.assertEqual(self.certificate(uid=4).status_code,404)

    def test_student_sees_only_own_report_and_teacher_cannot_export(self):
        self.proposal()
        self.assertEqual([r['aluno_id'] for r in self.report(uid=4).json['totais']],[1])
        self.assertEqual(self.report(uid=3,turma_disciplina_id=1).status_code,403)
        self.assertEqual(self.clients[2].get('/frequencia/relatorio',query_string={
            'turma_disciplina_id':1,'inicio':self.day,'fim':self.day,'formato':'csv'}).status_code,403)
        self.assertEqual(self.clients[1].get('/frequencia/relatorio?formato=csv').status_code,200)

    def test_form_requires_csrf_even_without_origin_header(self):
        self.assertEqual(self.clients[2].post('/frequencia/chamadas',data={}).status_code,403)

    def test_anonymous_and_invalid_bearer_do_not_inherit_cookie(self):
        self.assertEqual(self.app.test_client().get('/frequencia?formato=json').status_code,403)
        self.assertEqual(self.clients[1].get('/frequencia?formato=json',headers={'Authorization':'Bearer invalid'}).status_code,401)

    def test_missing_idempotency_and_invalid_request_have_no_effect(self):
        response = self.clients[2].post('/frequencia/chamadas',json={},headers={'Authorization':'Bearer '+self.tokens[2]})
        self.assertEqual(response.status_code,428)
        self.assertEqual(self.post(2,'/frequencia/chamadas',[]).status_code,400)
        self.assertEqual(self.proposal(turma_disciplina_id='²').status_code,400)
        self.assertEqual(self.proposal(aula=21).status_code,400)
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),0)

    def test_explicit_assignment_overrides_legacy_permissions(self):
        with get_session() as db:
            db.add(AtribuicaoDocenteModel(professor_id=2,turma_disciplina_id=1,ativo=True))
            db.commit()
        self.assertEqual(self.proposal().status_code,403)
        self.assertEqual(self.proposal(uid=3).status_code,201)

    def test_archiving_class_blocks_pending_approval(self):
        rid = self.legacy_pending().json['id']
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=1,arquivada=True))
            db.commit()
        self.assertEqual(self.decision('chamada',rid).status_code,409)
        self.assertEqual(self.report().json['totais'],[])

    def test_inactive_teacher_token_is_rejected_before_writing(self):
        with get_session() as db:
            db.query(UsuarioModel).filter_by(id=2).update({'estado':'pendente'})
            db.commit()
        self.assertEqual(self.proposal().status_code,401)

    def test_decision_replay_is_idempotent_and_second_decision_conflicts(self):
        rid = self.legacy_pending().json['id']
        body = {'decisao':'aprovar','versao':1,'motivo':'Chamada conferida'}
        first = self.post(1,f'/frequencia/chamada/{rid}/decidir',body,key='decision')
        replay = self.post(1,f'/frequencia/chamada/{rid}/decidir',body,key='decision')
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.json,replay.json)
        self.assertEqual(self.decision('chamada',rid,decision='rejeitar',version=2).status_code,409)

    def test_rejected_certificate_preserves_unjustified_absence(self):
        self.proposal()
        rid = self.certificate().json['id']
        self.assertEqual(self.decision('atestado',rid,decision='rejeitar').status_code,200)
        row = self.report().json['totais'][1]
        self.assertEqual((row['faltas'],row['justificadas']),(1,0))

    def test_certificate_accepted_before_call_justifies_direct_confirmation(self):
        self.decision('atestado',self.certificate().json['id'])
        self.proposal()
        self.assertEqual(self.report().json['totais'][1]['justificadas'],1)

    def test_invalid_oversized_or_missing_certificate_does_not_create_files(self):
        headers = {'Authorization':'Bearer '+self.tokens[5]}
        for content in [b'<html>invalid</html>', b'%PDF-'+b'x'*(5*1024*1024)]:
            response = self.clients[5].post('/frequencia/atestados?formato=json',data={
                'aluno_id':'2','inicio':self.day,'fim':self.day,'arquivo':(io.BytesIO(content),'test.pdf')},headers=headers)
            self.assertEqual(response.status_code,400)
        self.assertEqual(self.clients[5].post('/frequencia/atestados?formato=json',data={},headers=headers).status_code,400)
        self.assertEqual(list(Path(self.folder.name).rglob('*.enc')),[])

    def test_report_interval_percentages_and_detailed_scope(self):
        self.proposal()
        second = self.proposal(aula=2,presencas={'1':'falta','2':'presente'}).json['id']
        rows = self.report().json['totais']
        self.assertEqual([r['percentual_presenca'] for r in rows],['50.00','50.00'])
        self.assertEqual(self.report(inicio='2999-01-01').status_code,400)
        self.assertEqual(self.report(inicio='2000-01-01').status_code,400)
        own = self.report(uid=2,turma_disciplina_id=1).json
        self.assertTrue(all(r['turma']=='Turma 1' and r['materia']=='Matéria 1' for r in own['registros']))

    def test_csv_escapes_formula_and_excludes_certificate_details(self):
        with get_session() as db:
            db.query(AlunoModel).filter_by(id=1).update({'nome':'=HYPERLINK("test")'})
            db.commit()
        self.proposal()
        self.certificate()
        result = self.clients[1].get('/frequencia/relatorio',query_string={
            'inicio':self.day,'fim':self.day,'formato':'csv'})
        self.assertEqual(result.status_code,200)
        self.assertIn("'=HYPERLINK",result.text)
        self.assertNotIn('.enc',result.text)
        self.assertEqual(result.headers['Cache-Control'],'no-store')

    def test_certificate_failure_rolls_back_file_and_database(self):
        with patch('app.routes.frequencia_routes.finish_submission',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.certificate()
        self.assertEqual(list(Path(self.folder.name).rglob('*.enc')),[])
        with get_session() as db:
            self.assertEqual(db.query(AtestadoModel).count(),0)

    def test_missing_schema_is_503_without_creating_tables_or_breaking_login(self):
        PresencaModel.__table__.drop(engine)
        before = inspect(engine).get_table_names()
        self.assertEqual(self.clients[1].get('/frequencia?formato=json').status_code,503)
        self.assertEqual(before,inspect(engine).get_table_names())
        self.assertEqual(self.clients[1].get('/admin/dashboard').status_code,200)

    @unittest.skipUnless(engine.dialect.name == 'mysql', 'Concorrência exige MySQL descartável')
    def test_two_simultaneous_submissions_have_one_confirmed_call(self):
        barrier = threading.Barrier(2)
        body = {'turma_disciplina_id':1,'dia':self.day,'aula':1,'presencas':{'1':'presente','2':'falta'}}
        def send(_):
            client = self.app.test_client()
            barrier.wait(timeout=10)
            return client.post('/frequencia/chamadas', json=body, headers={
                'Authorization':'Bearer '+self.tokens[2], 'Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            statuses = list(workers.map(send, range(2)))
        self.assertEqual(sorted(statuses),[201,409])
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),1)
            self.assertEqual(db.query(ChamadaModel).one().estado,'aprovada')

    @unittest.skipUnless(engine.dialect.name == 'mysql', 'Concorrência exige MySQL descartável')
    def test_two_simultaneous_corrections_have_one_current_revision(self):
        rid = self.proposal().json['id']
        barrier = threading.Barrier(2)
        data = {'turma_disciplina_id':1,'dia':self.day,'aula':1,'anterior_id':rid,
                'versao':1,'motivo':'Correção simultânea','presencas':{'1':'presente','2':'presente'}}
        def send(_):
            client = self.app.test_client()
            barrier.wait(timeout=10)
            return client.post('/frequencia/chamadas',json=data,headers={
                'Authorization':'Bearer '+self.tokens[2], 'Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            self.assertEqual(sorted(workers.map(send,range(2))),[201,409])
        with get_session() as db:
            self.assertEqual(db.query(ChamadaModel).count(),2)
            self.assertEqual(db.query(ChamadaModel).filter_by(estado='aprovada').count(),1)
            self.assertEqual(db.get(ChamadaModel,rid).estado,'substituida')

    @unittest.skipUnless(engine.dialect.name == 'mysql', 'Concorrência exige MySQL descartável')
    def test_two_simultaneous_decisions_have_one_approval(self):
        rid = self.legacy_pending().json['id']
        barrier = threading.Barrier(2)
        def decide(_):
            client = self.app.test_client()
            barrier.wait(timeout=10)
            return client.post(f'/frequencia/chamada/{rid}/decidir', json={
                'decisao':'aprovar','versao':1,'motivo':'Conferência simultânea'}, headers={
                'Authorization':'Bearer '+self.tokens[1], 'Idempotency-Key':uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            statuses = list(workers.map(decide, range(2)))
        self.assertEqual(sorted(statuses),[200,409])
