"""Matrícula do aluno nas disciplinas da própria turma (achado no ensaio do vídeo, 24/11/2026).

Sem `alunos_disciplinas`, o aluno não vê materiais nem cursos. A matrícula acompanha a turma na
tela única "Turmas" (U5: a tela antiga foi aposentada).
"""
from unittest import TestCase

import test_concurrency as fixtures
from app.database import get_session
from app.models import (AlunoDisciplinaModel, AlunoTurmaModel, DisciplinaModel, ProfessorDisciplinaModel,
                        ProfessorTurmaModel, TurmaDisciplinaModel, TurmaModel)

CSRF = 'matricula-csrf'


class MatriculaDisciplinasTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with get_session() as db:  # turma nova, vazia, e uma segunda disciplina da professora
            db.query(AlunoTurmaModel).delete()
            db.query(ProfessorTurmaModel).delete()
            db.query(TurmaDisciplinaModel).delete()
            db.add_all([TurmaModel(id=2, nome='1º ano B', codigo='1B', ano_letivo=2026),
                        DisciplinaModel(id=2, nome='Física', codigo='FIS', carga_horaria=40),
                        ProfessorDisciplinaModel(professor_id=1, disciplina_id=2)])
            db.commit()

    def matriculas(self):
        with get_session() as db:
            return sorted(db.query(AlunoDisciplinaModel.aluno_id, AlunoDisciplinaModel.disciplina_id).all())

    def admin(self):
        client = self.fixture.client(1)
        with client.session_transaction() as session:
            session['csrf_token'] = CSRF
        return client

    def form(self, client, **dados):
        response = client.post('/admin/gestao-turmas', data={**dados, 'csrf_token': CSRF})
        self.assertEqual(response.status_code, 302, response.get_data(as_text=True)[:300])

    def test_matricula_nas_disciplinas_da_turma(self):
        client = self.admin()
        self.form(client, acao='atribuir', turma_id=2, professor_id=1, disciplina_id=1)
        self.form(client, acao='atribuir', turma_id=2, professor_id='', disciplina_id=2)
        self.assertEqual(self.matriculas(), [])
        self.form(client, acao='matricular', aluno_id=1, turma_id=2)
        self.assertEqual(self.matriculas(), [(1, 1), (1, 2)])

    def test_aluno_ja_na_turma_entra_na_disciplina_nova(self):
        client = self.admin()
        self.form(client, acao='matricular', aluno_id=1, turma_id=2)
        self.assertEqual(self.matriculas(), [])
        self.form(client, acao='atribuir', turma_id=2, professor_id=1, disciplina_id=1)
        self.form(client, acao='atribuir', turma_id=2, professor_id='', disciplina_id=2)
        self.assertEqual(self.matriculas(), [(1, 1), (1, 2)])

    def test_gestao_academica_atribui_matricula_e_desmatricula(self):
        client = self.admin()

        def post(dados):
            response = client.post('/admin/gestao-turmas', json=dados, headers={'X-CSRF-Token': CSRF})
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        post({'acao': 'matricular', 'turma_id': 2, 'aluno_id': 1})
        post({'acao': 'atribuir', 'turma_id': 2, 'professor_id': 1, 'disciplina_id': 2})
        self.assertEqual(self.matriculas(), [(1, 2)])
        # Outra turma do aluno também oferece Física: sair da 1º ano B não retira Física.
        with get_session() as db:
            db.add_all([AlunoTurmaModel(aluno_id=1, turma_id=1), TurmaDisciplinaModel(turma_id=1, disciplina_id=2)])
            db.commit()
        post({'acao': 'desmatricular', 'turma_id': 2, 'aluno_id': 1})
        self.assertEqual(self.matriculas(), [(1, 2)])
        post({'acao': 'desmatricular', 'turma_id': 1, 'aluno_id': 1})
        self.assertEqual(self.matriculas(), [])

    def test_aluno_matriculado_pela_interface_ve_a_disciplina(self):
        client = self.admin()
        self.form(client, acao='atribuir', turma_id=2, professor_id=1, disciplina_id=1)
        self.form(client, acao='atribuir', turma_id=2, professor_id=1, disciplina_id=2)
        self.form(client, acao='matricular', aluno_id=1, turma_id=2)
        html = self.fixture.client(2).get('/estudos').get_data(as_text=True)
        self.assertIn('Física', html)
        self.assertIn('Matematica', html)
