"""A turma inteira é registrada na matéria (pedido do usuário, 24/11/2026).

Registrar a turma numa disciplina matricula todos os seus alunos de uma vez; quem entra na
turma depois herda todas as matérias dela. Professor associado a turma que já tem matérias
não traz as outras matérias dele. A matéria só sai da turma enquanto não tiver histórico.
"""
from unittest import TestCase

from werkzeug.security import generate_password_hash

import test_concurrency as fixtures
from app.database import get_session
from app.models import (AlunoDisciplinaModel, AlunoModel, AlunoTurmaModel, AvaliacaoModel, DisciplinaModel,
                        EstadoTurmaModel, PeriodoLetivoModel, ProfessorDisciplinaModel, ProfessorTurmaModel,
                        TurmaDisciplinaModel, TurmaModel, UsuarioModel)


class TurmaMateriaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with get_session() as db:  # 1º ano B vazio, dois alunos e uma segunda matéria (Física)
            db.query(AlunoTurmaModel).delete()
            db.query(ProfessorTurmaModel).delete()
            db.query(TurmaDisciplinaModel).delete()
            db.add(UsuarioModel(id=5, email='u5@example.test', senha=generate_password_hash('test-password-123'),
                                tipo='aluno'))
            db.flush()
            db.add_all([AlunoModel(id=2, usuario_id=5, nome='Aluna 2', matricula='M2'),
                        TurmaModel(id=2, nome='1º ano B', codigo='1B', ano_letivo=2026),
                        DisciplinaModel(id=2, nome='Física', codigo='FIS', carga_horaria=40)])
            db.flush()
            db.add_all([AlunoTurmaModel(aluno_id=1, turma_id=2), AlunoTurmaModel(aluno_id=2, turma_id=2)])
            db.commit()
        self.client = self.fixture.client(1)

    def post(self, **dados):
        return self.client.post('/admin/turmas', data=dados)

    def matriculas(self):
        with get_session() as db:
            return sorted(db.query(AlunoDisciplinaModel.aluno_id, AlunoDisciplinaModel.disciplina_id).all())

    def materias(self, turma_id=2):
        with get_session() as db:
            return sorted(d for d, in db.query(TurmaDisciplinaModel.disciplina_id).filter_by(turma_id=turma_id))

    def test_registrar_turma_matricula_todos_os_alunos_de_uma_vez(self):
        self.assertEqual(self.post(action='associate_subject', turma_id=2, disciplina_id=2).status_code, 302)
        self.assertEqual(self.materias(), [2])
        self.assertEqual(self.matriculas(), [(1, 2), (2, 2)])
        html = self.client.get('/admin/turmas').get_data(as_text=True)
        self.assertIn('Registrar Turma na Matéria', html)
        self.assertIn('2 alunos', html)

    def test_aluno_que_entra_depois_herda_todas_as_materias(self):
        self.post(action='associate_subject', turma_id=2, disciplina_id=1)
        self.post(action='associate_subject', turma_id=2, disciplina_id=2)
        with get_session() as db:
            db.query(AlunoTurmaModel).filter_by(aluno_id=2).delete()
            db.query(AlunoDisciplinaModel).filter_by(aluno_id=2).delete()
            db.commit()
        self.assertEqual(self.post(action='associate_student', aluno_id=2, turma_id=2).status_code, 302)
        self.assertIn((2, 1), self.matriculas())
        self.assertIn((2, 2), self.matriculas())

    def test_registro_repetido_arquivada_e_dados_invalidos_sao_recusados(self):
        self.post(action='associate_subject', turma_id=2, disciplina_id=2)
        html = self.post(action='associate_subject', turma_id=2, disciplina_id=2).get_data(as_text=True)
        self.assertIn('ja esta registrada nesta materia', html)
        self.assertIn('Materia nao encontrada', self.post(action='associate_subject', turma_id=2, disciplina_id=99).get_data(as_text=True))
        self.assertIn('obrigatorias', self.post(action='associate_subject', turma_id=2).get_data(as_text=True))
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=2, arquivada=True))
            db.commit()
        self.assertIn('Turma arquivada', self.post(action='associate_subject', turma_id=2, disciplina_id=1).get_data(as_text=True))
        self.assertEqual(self.materias(), [2])

    def test_somente_admin_registra_turma_na_materia(self):
        for user in (2, 3):
            response = self.fixture.client(user).post('/admin/turmas', data={
                'action': 'associate_subject', 'turma_id': 2, 'disciplina_id': 2})
            self.assertIn(response.status_code, (302, 401, 403))
        self.assertEqual(self.materias(), [])
        self.assertEqual(self.matriculas(), [])

    def test_professor_em_turma_com_materias_nao_traz_outras_materias(self):
        # O professor 1 leciona Matemática e Física; a turma só tem Física.
        with get_session() as db:
            db.add(ProfessorDisciplinaModel(professor_id=1, disciplina_id=2))
            db.commit()
        self.post(action='associate_subject', turma_id=2, disciplina_id=2)
        self.assertEqual(self.post(action='associate_teacher', professor_id=1, turma_id=2).status_code, 302)
        self.assertEqual(self.materias(), [2])
        self.assertEqual(self.matriculas(), [(1, 2), (2, 2)])

    def test_professor_sem_materia_da_turma_e_recusado(self):
        self.post(action='associate_subject', turma_id=2, disciplina_id=2)  # o professor 2 só leciona Matemática
        html = self.post(action='associate_teacher', professor_id=2, turma_id=2).get_data(as_text=True)
        self.assertIn('nao leciona nenhuma materia desta turma', html)
        with get_session() as db:
            self.assertIsNone(db.query(ProfessorTurmaModel).filter_by(professor_id=2, turma_id=2).first())
        self.assertEqual(self.materias(), [2])

    def test_turma_sem_materias_mantem_fluxo_antigo_do_professor(self):
        self.assertEqual(self.post(action='associate_teacher', professor_id=1, turma_id=2).status_code, 302)
        self.assertEqual(self.materias(), [1])
        self.assertEqual(self.matriculas(), [(1, 1), (2, 1)])

    def test_retirar_materia_preserva_a_cursada_em_outra_turma(self):
        self.post(action='associate_subject', turma_id=2, disciplina_id=2)
        with get_session() as db:  # o aluno 1 também está na Turma 1, que oferece Física
            db.add_all([AlunoTurmaModel(aluno_id=1, turma_id=1), TurmaDisciplinaModel(turma_id=1, disciplina_id=2)])
            db.commit()
        self.assertEqual(self.post(action='remove_subject', turma_id=2, disciplina_id=2).status_code, 302)
        self.assertEqual(self.materias(), [])
        self.assertEqual(self.matriculas(), [(1, 2)])

    def test_materia_com_historico_nao_e_retirada(self):
        self.post(action='associate_subject', turma_id=2, disciplina_id=2)
        with get_session() as db:
            vinculo = db.query(TurmaDisciplinaModel).filter_by(turma_id=2, disciplina_id=2).one()
            periodo = PeriodoLetivoModel(turma_id=2, nome='1º bimestre', ordem=1)
            db.add(periodo)
            db.flush()
            db.add(AvaliacaoModel(turma_disciplina_id=vinculo.id, periodo_id=periodo.id, titulo='Prova', peso=1))
            db.commit()
        html = self.post(action='remove_subject', turma_id=2, disciplina_id=2).get_data(as_text=True)
        self.assertIn('nao pode ser retirada', html)
        self.assertEqual(self.materias(), [2])
        self.assertEqual(self.matriculas(), [(1, 2), (2, 2)])

    def test_aluno_da_turma_registrada_ve_a_materia(self):
        self.post(action='associate_subject', turma_id=2, disciplina_id=2)
        html = self.fixture.client(2).get('/estudos').get_data(as_text=True)
        self.assertIn('Física', html)
