"""A turma inteira é registrada na matéria (pedido do usuário, 24/11/2026), agora na tela única "Turmas" (U5).

Registrar a turma numa disciplina matricula todos os seus alunos de uma vez; quem entra na
turma depois herda todas as matérias dela. A matéria pode ser registrada antes de ter professor
e só sai da turma enquanto não tiver histórico. A tela antiga (/admin/turmas) foi aposentada.
"""
from unittest import TestCase

from werkzeug.security import generate_password_hash

import test_concurrency as fixtures
from app.database import get_session
from app.models import (AlunoDisciplinaModel, AlunoModel, AlunoTurmaModel, AvaliacaoModel, DisciplinaModel,
                        EstadoTurmaModel, PeriodoLetivoModel, ProfessorDisciplinaModel, ProfessorTurmaModel,
                        TurmaDisciplinaModel, TurmaModel, UsuarioModel)

CSRF = 'turmas-csrf'


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
        self.client = self.cliente(1)

    def cliente(self, user):
        client = self.fixture.client(user)
        with client.session_transaction() as session:
            session['csrf_token'] = CSRF
        return client

    def post(self, client=None, **dados):
        return (client or self.client).post('/admin/gestao-turmas', data={**dados, 'csrf_token': CSRF})

    def registrar(self, turma_id=2, disciplina_id=2, **extra):
        return self.post(acao='atribuir', turma_id=turma_id, disciplina_id=disciplina_id, professor_id='', **extra)

    def matriculas(self):
        with get_session() as db:
            return sorted(db.query(AlunoDisciplinaModel.aluno_id, AlunoDisciplinaModel.disciplina_id).all())

    def materias(self, turma_id=2):
        with get_session() as db:
            return sorted(d for d, in db.query(TurmaDisciplinaModel.disciplina_id).filter_by(turma_id=turma_id))

    def test_registrar_turma_matricula_todos_os_alunos_de_uma_vez(self):
        self.assertEqual(self.registrar().status_code, 302)
        self.assertEqual(self.materias(), [2])
        self.assertEqual(self.matriculas(), [(1, 2), (2, 2)])
        html = self.client.get('/admin/gestao-turmas').get_data(as_text=True)
        self.assertIn('Matéria e professor', html)
        self.assertIn('2 alunos', html)
        self.assertIn('Ainda sem professor', html)

    def test_aluno_que_entra_depois_herda_todas_as_materias(self):
        self.registrar(disciplina_id=1)
        self.registrar(disciplina_id=2)
        with get_session() as db:
            db.query(AlunoTurmaModel).filter_by(aluno_id=2).delete()
            db.query(AlunoDisciplinaModel).filter_by(aluno_id=2).delete()
            db.commit()
        self.assertEqual(self.post(acao='matricular', aluno_id=2, turma_id=2).status_code, 302)
        self.assertIn((2, 1), self.matriculas())
        self.assertIn((2, 2), self.matriculas())

    def test_registro_repetido_arquivada_e_dados_invalidos_sao_recusados(self):
        self.registrar()
        repetido = self.registrar()
        self.assertEqual(repetido.status_code, 409)
        self.assertIn('já está registrada nesta matéria', repetido.get_data(as_text=True))
        self.assertEqual(self.registrar(disciplina_id=99).status_code, 404)
        self.assertEqual(self.post(acao='atribuir', turma_id=2, professor_id='').status_code, 400)
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=2, arquivada=True))
            db.commit()
        arquivada = self.registrar(disciplina_id=1)
        self.assertEqual(arquivada.status_code, 409)
        self.assertIn('Turma arquivada', arquivada.get_data(as_text=True))
        self.assertEqual(self.materias(), [2])

    def test_somente_admin_registra_turma_na_materia(self):
        for user in (2, 3):
            response = self.registrar(client=self.cliente(user))
            self.assertIn(response.status_code, (302, 400, 401, 403, 428))  # professor cai no fluxo de aprovação, que recusa
        self.assertEqual(self.materias(), [])
        self.assertEqual(self.matriculas(), [])

    def test_professor_atribuido_nao_traz_outras_materias_dele(self):
        # O professor 1 leciona Matemática e Física; a turma recebe só Física, com ele.
        with get_session() as db:
            db.add(ProfessorDisciplinaModel(professor_id=1, disciplina_id=2))
            db.commit()
        self.assertEqual(self.post(acao='atribuir', turma_id=2, disciplina_id=2, professor_id=1).status_code, 302)
        self.assertEqual(self.materias(), [2])
        self.assertEqual(self.matriculas(), [(1, 2), (2, 2)])

    def test_atribuicao_com_professor_inexistente_e_recusada(self):
        self.assertEqual(self.post(acao='atribuir', turma_id=2, disciplina_id=2, professor_id=99).status_code, 404)
        self.assertEqual(self.materias(), [])

    def test_retirar_materia_preserva_a_cursada_em_outra_turma(self):
        self.registrar()
        with get_session() as db:  # o aluno 1 também está na Turma 1, que oferece Física
            db.add_all([AlunoTurmaModel(aluno_id=1, turma_id=1), TurmaDisciplinaModel(turma_id=1, disciplina_id=2)])
            db.commit()
        self.assertEqual(self.post(acao='retirar_materia', turma_id=2, disciplina_id=2).status_code, 302)
        self.assertEqual(self.materias(), [])
        self.assertEqual(self.matriculas(), [(1, 2)])

    def test_materia_com_historico_nao_e_retirada(self):
        self.registrar()
        with get_session() as db:
            vinculo = db.query(TurmaDisciplinaModel).filter_by(turma_id=2, disciplina_id=2).one()
            periodo = PeriodoLetivoModel(turma_id=2, nome='1º bimestre', ordem=1)
            db.add(periodo)
            db.flush()
            db.add(AvaliacaoModel(turma_disciplina_id=vinculo.id, periodo_id=periodo.id, titulo='Prova', peso=1))
            db.commit()
        response = self.post(acao='retirar_materia', turma_id=2, disciplina_id=2)
        self.assertEqual(response.status_code, 409)
        self.assertIn('não pode ser retirada', response.get_data(as_text=True))
        self.assertEqual(self.materias(), [2])
        self.assertEqual(self.matriculas(), [(1, 2), (2, 2)])

    def test_aluno_da_turma_registrada_ve_a_materia(self):
        self.registrar()
        html = self.fixture.client(2).get('/estudos').get_data(as_text=True)
        self.assertIn('Física', html)

    def test_tela_antiga_de_turmas_foi_aposentada(self):
        antiga = self.client.get('/admin/turmas')
        self.assertEqual(antiga.status_code, 301)
        self.assertTrue(antiga.headers['Location'].endswith('/admin/gestao-turmas'))
        envio = self.client.post('/admin/turmas', data={'action': 'associate_subject', 'turma_id': 2, 'disciplina_id': 2},
                                 headers={'Accept': 'text/html'})
        self.assertEqual(envio.status_code, 410)
        self.assertIn('unificada em Turmas', envio.get_data(as_text=True))
        self.assertEqual(self.materias(), [])

    def test_turno_na_criacao_e_na_edicao(self):
        self.assertEqual(self.post(acao='criar', nome='2º ano A', codigo='2A', ano_letivo=2026, turno='Vespertino').status_code, 302)
        with get_session() as db:
            turma = db.query(TurmaModel).filter_by(codigo='2A').one()
            self.assertEqual(turma.turno, 'Vespertino')
            turma_id = turma.id
        self.post(acao='editar', turma_id=turma_id, nome='2º ano A', ano_letivo=2026, turno='')
        with get_session() as db:
            self.assertIsNone(db.get(TurmaModel, turma_id).turno)
        self.assertEqual(self.post(acao='criar', nome='Outra', codigo='2A', ano_letivo=2026).status_code, 409)
