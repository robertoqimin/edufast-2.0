"""Security contracts for admission, delegation, scoped data and approval effects."""
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase, skipUnless
from uuid import uuid4

from werkzeug.security import generate_password_hash
from unittest.mock import patch
import test_concurrency as fixtures
from app import create_app
from app.database import engine, get_session
from app.models import (AlunoModel, AtividadeModel, DocumentoModel, NotaModel, ProfessorTurmaModel,
                        SolicitacaoAlteracaoModel, SolicitacaoDocumentoModel, TurmaModel, UsuarioModel)


class ApprovalSecurityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with get_session() as db:
            db.add_all([UsuarioModel(id=5, email='super@example.test', senha=generate_password_hash('test-password-123'), tipo='super_admin'),
                        UsuarioModel(id=6, email='other@example.test', senha=generate_password_hash('test-password-123'), tipo='aluno')])
            db.flush()
            db.add(AlunoModel(id=2, usuario_id=6, nome='Outro aluno', matricula='OTHER', cpf='88888888888'))
            db.query(AlunoModel).filter_by(id=1).update({'cpf': '99999999999'}, synchronize_session=False)
            db.commit()

    def client(self, user=1):
        client = self.app.test_client()
        with get_session() as db:
            row = db.get(UsuarioModel, user)
            with client.session_transaction() as session:
                session.update(user_id=row.id, user_role=row.tipo, user_email=row.email, auth_version=row.auth_version)
        return client

    def token(self, user):
        with get_session() as db:
            email = db.get(UsuarioModel, user).email
        response = self.app.test_client().post('/login', json={'email': email, 'senha': 'test-password-123'})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return {'Authorization': 'Bearer ' + response.json['token']}

    def count(self, model):
        return self.fixture.count(model)

    def submit(self, kind, payload, user=3, key=None):
        return self.client(user).post('/solicitacoes/alteracoes', json={'tipo': kind, 'payload': payload},
            headers={'Idempotency-Key': key or uuid4().hex})

    def approve(self, proposal, user=1):
        return self.client(user).post(f'/solicitacoes/alteracoes/{proposal}/decidir', json={'decisao': 'aprovar'})

    def activity(self):
        return {'turma_id': 1, 'disciplina_id': 1, 'titulo': 'Aula proposta', 'descricao': 'Material sintetico'}

    def test_malformed_proposal_kind_is_rejected_without_effect(self):
        for kind in [None, [], {}, 42, 'cadastro', 'unknown']:
            with self.subTest(kind=kind):
                self.assertEqual(self.submit(kind, {}).status_code, 400)
        self.assertEqual(self.count(SolicitacaoAlteracaoModel), 0)

    def test_approved_document_response_replays_without_second_effect(self):
        def send(key):
            return self.client(3).post('/professor/documentos/upload',
                data=self.fixture.upload(solicitacao_id='2', idempotency_key=key))
        self.assertEqual(send('original-response').status_code, 302)
        with get_session() as db:
            proposal_id = db.query(SolicitacaoAlteracaoModel).one().id
        self.assertEqual(self.approve(proposal_id).status_code, 200)
        self.assertEqual(send('original-response').status_code, 302)
        self.assertEqual(send('new-response').status_code, 409)
        self.assertEqual(self.count(DocumentoModel), 1)
        self.assertEqual(len(self.fixture.files()), 1)

    def test_browser_mutations_require_same_origin_and_csrf_token(self):
        client = self.client(3)
        page = client.get('/solicitacoes')
        self.assertEqual(page.status_code, 200)
        with client.session_transaction() as session:
            token = session['csrf_token']
        data = {'tipo': 'criar_turma', 'nome': 'Nova', 'codigo': 'CSRF',
                'ano_letivo': '2026', 'turno': 'Manha', 'idempotency_key': uuid4().hex}
        self.assertEqual(client.post('/solicitacoes/alteracoes', data=data,
            headers={'Origin': 'https://evil.example', 'X-CSRF-Token': token}).status_code, 403)
        self.assertEqual(client.post('/solicitacoes/alteracoes', data=data,
            headers={'Origin': 'http://localhost'}).status_code, 403)
        self.assertEqual(self.count(SolicitacaoAlteracaoModel), 0)
        self.assertEqual(client.post('/solicitacoes/alteracoes', data={**data, 'csrf_token': token},
            headers={'Origin': 'http://localhost'}).status_code, 302)
        self.assertEqual(self.count(SolicitacaoAlteracaoModel), 1)

    def test_admin_ajax_registration_pages_carry_csrf_and_accept_submission(self):
        client = self.client()
        for path in ['/admin/cadastro-alunos', '/admin/cadastro-professores']:
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="csrf_token"', response.data)
        with client.session_transaction() as session:
            token = session['csrf_token']
        response = client.post('/cadastro/professor', data={
            'nome': 'Cadastro pelo painel', 'email': 'browser-prof@example.test',
            'senha': 'test-password-123', 'cpf': '12312312312',
            'idempotency_key': uuid4().hex, 'csrf_token': token},
            headers={'Origin': 'http://localhost'})
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))

    def test_public_registration_cannot_choose_authority_or_active_state(self):
        body = {'nome': 'Candidato', 'email': 'pending@example.test', 'senha': 'test-password-123',
                'tipo': 'professor', 'cpf': '77777777777', 'estado': 'ativo', 'revisor_materiais': True, 'status': 'Ativo'}
        response = self.app.test_client().post('/cadastro', json=body)
        self.assertEqual(response.status_code, 202)
        user_id = response.json['id']
        with get_session() as db:
            row = db.get(UsuarioModel, user_id)
            self.assertEqual((row.tipo, row.estado, row.revisor_materiais), ('pendente', 'pendente', False))
            proposal = db.query(SolicitacaoAlteracaoModel).filter_by(solicitante_id=user_id).one().id
        self.assertEqual(self.app.test_client().post('/login', json={'email': body['email'], 'senha': body['senha']}).status_code, 403)
        forged = self.app.test_client()
        with forged.session_transaction() as session:
            session.update(user_id=user_id, user_role='professor')
        self.assertEqual(forged.get('/professor/dashboard').status_code, 401)
        self.assertEqual(self.approve(proposal).status_code, 200)
        self.assertEqual(self.app.test_client().post('/login', json={'email': body['email'], 'senha': body['senha']}).status_code, 200)

    def test_public_registration_rejects_admin_and_superadmin(self):
        for role in ['admin', 'super_admin', 'ADMIN', 'professor_gestor']:
            response = self.app.test_client().post('/cadastro', json={'nome': 'X', 'email': 'x@example.test', 'senha': 'x', 'tipo': role})
            self.assertEqual(response.status_code, 400)

    def test_admin_and_superadmin_create_approved_teacher_directly(self):
        for user in [1, 5]:
            response = self.client(user).post('/cadastro/professores', json={'nome': 'Docente', 'email': f'direct{user}@example.test', 'senha': 'test-password-123', 'cpf': f'4444444444{user}'})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json['estado'], 'ativo')

    def test_rejected_admission_stays_without_privileges(self):
        response = self.app.test_client().post('/cadastro', json={'nome': 'X', 'email': 'reject@example.test', 'senha': 'test-password-123', 'tipo': 'aluno', 'matricula': 'PEND', 'status': 'Ativo'})
        with get_session() as db:
            request_id = db.query(SolicitacaoAlteracaoModel).filter_by(solicitante_id=response.json['id']).one().id
            self.assertEqual(db.query(AlunoModel).filter_by(usuario_id=response.json['id']).one().status_matricula, 'Pendente')
        result = self.client().post(f'/solicitacoes/alteracoes/{request_id}/decidir', json={'decisao': 'rejeitar', 'justificativa': 'Sem comprovacao'})
        self.assertEqual(result.json['estado'], 'rejeitada')
        self.assertEqual(self.approve(request_id).status_code, 409)

    def test_teacher_search_is_scoped_and_never_returns_cpf_or_birth_date(self):
        headers = self.token(3)
        client = self.app.test_client()
        for term in ['Aluno', 'M1', 'T1', 'Turma']:
            response = client.get('/alunos/busca', query_string={'termo': term}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual([row['matricula'] for row in response.json['alunos']], ['M1'])
            self.assertEqual(set(response.json['alunos'][0]), {'id', 'nome', 'matricula'})
        self.assertEqual(client.get('/alunos/busca?termo=99999999999', headers=headers).json['alunos'], [])
        self.assertEqual(client.get('/alunos/busca?cpf=99999999999', headers=headers).status_code, 403)
        self.assertEqual(client.get('/alunos/busca?termo=%25', headers=headers).json['alunos'], [])
        self.assertEqual(client.get('/alunos/busca?termo=OTHER', headers=headers).json['alunos'], [])

    def test_only_admin_roles_can_search_by_cpf(self):
        for user in [1, 5]:
            result = self.client(user).get('/alunos/busca?cpf=99999999999')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json['alunos'][0]['cpf'], '99999999999')
        self.assertEqual(self.client(2).get('/alunos/busca?cpf=99999999999').status_code, 403)

    def test_class_creation_is_pending_until_admin_decides(self):
        response = self.submit('criar_turma', {'nome': 'Nova turma', 'codigo': 'NEW', 'ano_letivo': 2027})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.count(TurmaModel), 1)
        self.assertEqual(self.approve(response.json['id']).status_code, 200)
        self.assertEqual(self.count(TurmaModel), 2)
        self.assertEqual(self.approve(response.json['id']).status_code, 409)
        with get_session() as db:
            row = db.get(SolicitacaoAlteracaoModel, response.json['id'])
            self.assertEqual((row.decidido_por, row.estado), (1, 'aprovada'))

    def test_teacher_cannot_decide_or_mutate_another_student(self):
        response = self.submit('editar_aluno', {'aluno_id': 2, 'nome': 'Tamper', 'versao': 1})
        self.assertEqual(response.status_code, 404)
        response = self.submit('criar_turma', {'nome': 'Nova', 'codigo': 'NEW', 'ano_letivo': 2027})
        self.assertEqual(self.approve(response.json['id'], user=3).status_code, 403)
        self.assertEqual(self.client(3).post('/admin/alunos/1/editar', data=self.fixture.student_edit()).status_code, 403)

    def test_teacher_student_change_requires_version_and_approval(self):
        response = self.submit('editar_aluno', {'aluno_id': 1, 'nome': 'Nome proposto', 'curso_serie': 'Serie 2', 'versao': 1})
        self.assertEqual(response.status_code, 202)
        with get_session() as db:
            self.assertEqual(db.get(AlunoModel, 1).nome, 'Aluno')
        self.assertEqual(self.approve(response.json['id']).status_code, 200)
        with get_session() as db:
            self.assertEqual((db.get(AlunoModel, 1).nome, db.get(AlunoModel, 1).versao), ('Nome proposto', 2))
        self.assertEqual(self.submit('editar_aluno', {'aluno_id': 1, 'nome': 'X', 'versao': 2, 'cpf': 'tamper'}).status_code, 400)

    def test_stale_target_rolls_back_decision_and_domain_effect(self):
        result = self.submit('editar_aluno', {'aluno_id': 1, 'nome': 'Proposta', 'versao': 1})
        self.assertEqual(self.client().post('/admin/alunos/1/editar', data=self.fixture.student_edit()).status_code, 302)
        self.assertEqual(self.approve(result.json['id']).status_code, 409)
        with get_session() as db:
            self.assertEqual(db.get(AlunoModel, 1).nome, 'Aluno editado')
            self.assertEqual(db.get(SolicitacaoAlteracaoModel, result.json['id']).estado, 'pendente')

    def test_approval_revalidates_revoked_teaching_assignment(self):
        result = self.submit('lancar_atividade', self.activity())
        with get_session() as db:
            db.query(ProfessorTurmaModel).filter_by(professor_id=1).delete()
            db.commit()
        self.assertEqual(self.approve(result.json['id']).status_code, 403)
        self.assertEqual(self.count(AtividadeModel), 0)

    def test_grade_write_is_a_proposal_with_no_immediate_effect(self):
        data = self.fixture.grade()
        data['idempotency_key'] = 'grade-proposal'
        result = self.client(3).post('/professor/notas/salvar', data=data)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.count(NotaModel), 0)
        with get_session() as db:
            request_id = db.query(SolicitacaoAlteracaoModel).one().id
        self.assertEqual(self.approve(request_id).status_code, 200)
        with get_session() as db:
            self.assertEqual(float(db.query(NotaModel).one().nota), 8)

    def test_material_reviewer_is_limited_and_cannot_approve_self(self):
        result = self.client().post('/admin/usuarios/4/permissoes', json={'revisor_materiais': True})
        self.assertEqual(result.status_code, 200)
        activity = self.submit('lancar_atividade', self.activity())
        self.assertEqual(self.approve(activity.json['id'], user=4).status_code, 200)
        grade = self.submit('salvar_nota', dict(self.fixture.grade()))
        self.assertEqual(self.approve(grade.json['id'], user=4).status_code, 403)
        self.assertEqual(self.client(4).get('/admin/dashboard').status_code, 403)
        self.assertEqual(self.client(4).get('/alunos/busca?cpf=99999999999').status_code, 403)
        self.assertEqual(self.client(4).post('/admin/usuarios/3/permissoes', json={'revisor_materiais': True}).status_code, 403)
        with get_session() as db:
            db.add(ProfessorTurmaModel(professor_id=2, turma_id=1))
            db.commit()
        own = self.submit('lancar_atividade', self.activity(), user=4)
        self.assertEqual(self.approve(own.json['id'], user=4).status_code, 403)

    def test_permission_revocation_invalidates_existing_authentication(self):
        old_cookie = self.client(4)
        old_token = self.token(4)
        self.assertEqual(self.client().post('/admin/usuarios/4/permissoes', json={'revisor_materiais': True}).status_code, 200)
        self.assertEqual(old_cookie.get('/professor/dashboard').status_code, 401)
        self.assertEqual(self.app.test_client().get('/professor/teste', headers=old_token).status_code, 401)

    def test_only_superadmin_can_grant_admin_role(self):
        self.assertEqual(self.client().post('/admin/usuarios/4/permissoes', json={'papel': 'admin'}).status_code, 403)
        self.assertEqual(self.client(5).post('/admin/usuarios/4/permissoes', json={'papel': 'admin'}).status_code, 200)
        self.assertEqual(self.client(4).get('/admin/dashboard').status_code, 200)

    def test_logout_revokes_bearer_and_cookie_copies(self):
        cookie, token = self.client(3), self.token(3)
        self.assertEqual(cookie.get('/logout').status_code, 302)
        self.assertEqual(self.app.test_client().get('/professor/teste', headers=token).status_code, 401)
        self.assertEqual(cookie.get('/professor/dashboard').status_code, 403)

    def test_document_submission_is_scoped_pending_and_private(self):
        data = self.fixture.upload(aluno_id='2', disciplina_id='1', idempotency_key='unrelated')
        self.assertEqual(self.client(3).post('/arquivos/upload', data=data).status_code, 404)
        data = self.fixture.upload(aluno_id='1', disciplina_id='1', idempotency_key='pending-doc')
        response = self.client(3).post('/arquivos/upload', data=data)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.count(DocumentoModel), 0)
        with get_session() as db:
            row = db.get(SolicitacaoAlteracaoModel, response.json['id'])
            filename = row.arquivo
        self.assertEqual(self.client(3).get('/arquivos/download/' + filename).status_code, 404)
        self.assertEqual(self.client(4).get(f"/solicitacoes/alteracoes/{response.json['id']}/arquivo").status_code, 404)
        self.assertEqual(self.approve(response.json['id']).status_code, 200)
        self.assertEqual(self.count(DocumentoModel), 1)

    def test_download_applies_same_ownership_with_cookie_and_bearer(self):
        response = self.client().post('/arquivos/upload', data=self.fixture.upload(aluno_id='1', idempotency_key='admin-doc'))
        self.assertEqual(response.status_code, 201)
        name = response.json['documento']['arquivo']
        for user, expected in [(2, 200), (6, 404), (4, 404), (1, 200), (5, 200)]:
            with self.subTest(user=user):
                self.assertEqual(self.client(user).get('/arquivos/download/' + name).status_code, expected)
                result = self.app.test_client().get('/arquivos/download/' + name, headers=self.token(user))
                self.assertEqual(result.status_code, expected)
                if expected == 200:
                    self.assertEqual(result.headers['Cache-Control'], 'private, no-store')
        self.assertEqual(self.app.test_client().get('/arquivos/download/' + name).status_code, 401)

    def test_proposals_cannot_replace_payload_or_inject_sensitive_fields(self):
        key = 'json-fingerprint'
        original = self.submit('criar_turma', {'nome': 'Original', 'codigo': 'ORIG', 'ano_letivo': 2027}, key=key)
        self.assertEqual(original.status_code, 202)
        self.assertEqual(self.submit('criar_turma', {'nome': 'Alterada', 'codigo': 'OTHER', 'ano_letivo': 2027}, key=key).status_code, 409)
        self.assertEqual(self.submit('criar_turma', {'nome': 'X', 'codigo': 'X', 'ano_letivo': 2027, 'estado': 'aprovada'}).status_code, 400)

    def test_secret_is_required_in_every_environment(self):
        from config import Config
        for mode in ['development', 'testing', 'production']:
            with patch.object(Config, 'APP_ENV', mode), patch.object(Config, 'SECRET_KEY', ''):
                with self.assertRaises(RuntimeError):
                    create_app()

    def test_approval_pages_and_no_cpf_in_teacher_responses(self):
        for user in [1, 3, 5]:
            response = self.client(user).get('/solicitacoes')
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client(2).get('/solicitacoes').status_code, 403)
        self.assertNotIn(b'99999999999', self.client(3).get('/professor/dashboard').data)

    @skipUnless(engine.dialect.name == 'mysql', 'Concurrency requires disposable MySQL')
    def test_two_approvals_have_only_one_domain_effect(self):
        result = self.submit('criar_turma', {'nome': 'Unica', 'codigo': 'ONCE', 'ano_letivo': 2027})
        barrier = threading.Barrier(2)
        def decide(user):
            client = self.client(user)
            barrier.wait(timeout=15)
            return client.post(f"/solicitacoes/alteracoes/{result.json['id']}/decidir", json={'decisao': 'aprovar'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(decide, [1, 5])), [200, 409])
        self.assertEqual(self.count(TurmaModel), 2)
