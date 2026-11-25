"""Existing observable admin contracts, before architectural moves."""
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from werkzeug.datastructures import MultiDict
from flask import session

import test_concurrency as fixtures
from app.controllers import admin_controller as admin
from app.database import get_session
from app.models import SolicitacaoDocumentoModel


class AdminCharacterization(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_date_and_status_presentation(self):
        self.assertEqual(admin.format_created_at(None), 'Sem data')
        self.assertEqual(admin.format_created_at('original'), 'original')
        self.assertEqual(admin.format_created_at(datetime(2026, 1, 2, 3, 4)), '02/01/2026 03:04')
        self.assertEqual(admin.format_relative_date(None), 'Agora')
        for value, expected in [(' Ativo ', 'status-active'), ('PENDENTE', 'status-pending'), ('inativo', 'status-inactive'), ('other', 'status-neutral')]:
            self.assertEqual(admin.status_class(value), expected)
        with patch.object(admin, 'date') as date:
            date.today.return_value = datetime(2026, 1, 3).date()
            self.assertEqual(admin.format_relative_date(datetime(2026, 1, 2)), 'Ha 1 dia')
        self.assertIsNone(admin._parse_optional_date(''))
        with self.assertRaises(ValueError):
            admin._parse_optional_date('invalid')

    def test_dashboard_keys_counts_and_order(self):
        data = admin.get_admin_data()
        self.assertEqual(set(data), {'total_alunos', 'total_professores', 'matriculas_pendentes', 'matriculas_hoje', 'alunos', 'professores', 'registros_recentes'})
        self.assertEqual((data['total_alunos'], data['total_professores']), (1, 2))
        self.assertEqual(data['alunos'][0]['matricula'], 'M1')
        self.assertEqual([p['id'] for p in data['professores']], [2, 1])

    def test_academic_page_contracts(self):
        self.assertEqual(admin.get_disciplinas(), [{'id': 1, 'nome': 'Matematica', 'codigo': 'MAT', 'carga_horaria': 40}])
        self.assertEqual(set(admin.get_disciplinas_page_data()), {'disciplinas', 'professores', 'professor_vinculos'})
        turmas = admin.get_turmas_page_data()
        self.assertEqual(set(turmas), {'turmas', 'alunos', 'professores', 'aluno_vinculos', 'professor_vinculos', 'disciplina_vinculos', 'disciplinas'})
        self.assertEqual(turmas['aluno_vinculos'][0]['matricula'], 'M1')

    def test_details_fallback_and_missing_records(self):
        self.assertEqual(admin.get_aluno_detail(None)['aluno']['id'], 1)
        self.assertEqual(admin.get_professor_detail(None)['professor']['id'], 2)
        from werkzeug.exceptions import NotFound
        with self.assertRaises(NotFound):
            admin.get_aluno_detail(999)

    def test_validation_errors_are_preserved(self):
        self.assertEqual(admin.criar_disciplina(MultiDict())[1], 400)
        self.assertEqual(admin.criar_disciplina(MultiDict({'nome': 'X', 'codigo': 'X', 'carga_horaria': '-1'})),
                         ({'erro': 'Carga horária não pode ser negativa'}, 400))
        self.assertEqual(admin.criar_turma(MultiDict({'nome': 'X', 'codigo': 'X', 'ano_letivo': '1999'})),
                         ({'erro': 'Ano letivo inválido'}, 400))
        self.assertEqual(admin.associar_aluno_turma(MultiDict({'aluno_id': '999', 'turma_id': '1'}))[1], 404)

    def test_request_and_communication_shapes(self):
        app = fixtures.MutationApiTests.app
        for fn, args, key in [(admin.request_student_document, (1,), 'student-request'),
                              (admin.request_professor_document, (1,), 'teacher-request')]:
            data = MultiDict({'titulo': ' Teste ', 'mensagem': ' Texto ', 'idempotency_key': key})
            with app.test_request_context('/', method='POST', data=data):
                session['user_id'] = 1
                body, status = fn(*args, data)
                self.assertEqual(status, 201)
                with get_session() as db:
                    row = db.get(SolicitacaoDocumentoModel, body['id'])
                    self.assertEqual((row.titulo, row.mensagem, row.status), ('Teste', 'Texto', 'pendente'))
        self.assertEqual(admin.get_comunicados(), [])
