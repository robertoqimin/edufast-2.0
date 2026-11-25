"""B4 — contratos (RED) das ofertas extras. Falham até a implementação ser aprovada e feita.

Pasta fora da regressão (não é pacote). Rodar à mão:
    PYTHONPATH="Codigos:.github/cicd/tests" python -m unittest discover -s .github/cicd/tests/b4_superior -v
Estudo: Documentos/planejamento/ESTUDO_ENSINO_SUPERIOR_B4_2026-11-24.md

API esperada (app.services.ofertas):
    criar_oferta(db, *, nome, codigo, ano_letivo, periodo_letivo, disciplina_id, vagas=None, inscricao_aberta=False) -> TurmaModel
    inscrever_turma(db, turma_id, oferta_id)      retirar_turma(db, turma_id, oferta_id)
    matricular_aluno(db, aluno_id, oferta_id)     autoinscrever(db, usuario_id, oferta_id)
Recusas lançam app.concurrency.MutationConflict (409 regra; 403 sem permissão).
"""
from unittest import TestCase

import test_concurrency as fixtures
from app.concurrency import MutationConflict
from app.database import get_session
from app.models import (AlunoDisciplinaModel, AlunoModel, AlunoTurmaModel, DisciplinaModel, TurmaDisciplinaModel,
                        TurmaModel, UsuarioModel)


def ofertas():
    from app.services import ofertas as servico  # ainda não existe: contrato RED
    return servico


class ContratosOfertasExtras(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with get_session() as db:  # turma regular 1 já tem o aluno 1; acrescenta colega e eletiva
            db.add_all([UsuarioModel(id=7, email='colega@example.test', senha='-', tipo='aluno'),
                        DisciplinaModel(id=9, nome='Robótica', codigo='ROB', carga_horaria=40),
                        DisciplinaModel(id=10, nome='Inglês', codigo='ING', carga_horaria=40)])
            db.flush()
            db.add(AlunoModel(id=7, usuario_id=7, nome='Colega', matricula='M7'))
            db.add(AlunoTurmaModel(aluno_id=7, turma_id=1))
            db.commit()

    def oferta(self, **extra):
        with get_session() as db:
            row = ofertas().criar_oferta(db, nome='Robótica — eletiva', codigo='ROB-26-1', ano_letivo=2026,
                                         periodo_letivo='2026/1', disciplina_id=9, **extra)
            db.commit()
            return row.id

    def na_oferta(self, oferta_id):
        with get_session() as db:
            return sorted(a for a, in db.query(AlunoTurmaModel.aluno_id).filter_by(turma_id=oferta_id))

    def test_oferta_tem_uma_disciplina_so(self):
        oid = self.oferta()
        with get_session() as db:
            self.assertEqual(db.get(TurmaModel, oid).tipo, 'oferta')
            from app.services.matriculas import registrar_disciplina
            with self.assertRaises(MutationConflict):
                registrar_disciplina(db, oid, 10)

    def test_turma_inscrita_leva_todos_os_alunos(self):
        oid = self.oferta()
        with get_session() as db:
            ofertas().inscrever_turma(db, 1, oid)
            db.commit()
            self.assertEqual(self.na_oferta(oid), [1, 7])
            self.assertTrue(db.query(AlunoDisciplinaModel).filter_by(aluno_id=7, disciplina_id=9).first())
            from app.services import frequencia_service
            pair = db.query(TurmaDisciplinaModel).filter_by(turma_id=oid).one()
            self.assertEqual([a.id for a in frequencia_service.students(db, pair)], [1, 7])

    def test_quem_entra_na_turma_depois_herda_a_oferta(self):
        oid = self.oferta()
        with get_session() as db:
            ofertas().inscrever_turma(db, 1, oid)
            db.add(UsuarioModel(id=8, email='novo@example.test', senha='-', tipo='aluno'))
            db.flush()
            db.add(AlunoModel(id=8, usuario_id=8, nome='Novo', matricula='M8'))
            db.commit()
        response = self.fixture.client(1).post('/admin/turmas', data={'action': 'associate_student', 'aluno_id': 8, 'turma_id': 1})
        self.assertEqual(response.status_code, 302)
        self.assertIn(8, self.na_oferta(oid))

    def test_quem_sai_da_turma_sai_da_oferta(self):
        oid = self.oferta()
        with get_session() as db:
            ofertas().inscrever_turma(db, 1, oid)
            db.commit()
        client = self.fixture.client(1)
        with client.session_transaction() as s:
            s['csrf_token'] = 'b4'
        client.post('/admin/gestao-turmas', json={'acao': 'desmatricular', 'turma_id': 1, 'aluno_id': 7}, headers={'X-CSRF-Token': 'b4'})
        self.assertEqual(self.na_oferta(oid), [1])

    def test_matricula_individual_vale_so_para_o_aluno(self):
        oid = self.oferta()
        with get_session() as db:
            ofertas().matricular_aluno(db, 1, oid)
            db.commit()
        self.assertEqual(self.na_oferta(oid), [1])

    def test_matricula_direta_prevalece_ao_retirar_a_turma(self):
        oid = self.oferta()
        with get_session() as db:
            ofertas().inscrever_turma(db, 1, oid)
            ofertas().matricular_aluno(db, 7, oid)
            db.commit()
            ofertas().retirar_turma(db, 1, oid)
            db.commit()
        self.assertEqual(self.na_oferta(oid), [7])

    def test_autoinscricao_so_em_oferta_aberta(self):
        fechada = self.oferta()
        with get_session() as db:
            with self.assertRaises(MutationConflict):
                ofertas().autoinscrever(db, 2, fechada)
            with self.assertRaises(MutationConflict):
                ofertas().autoinscrever(db, 2, 1)  # turma regular nunca aceita autoinscrição

    def test_autoinscricao_respeita_vagas_contando_alunos_da_turma(self):
        with get_session() as db:
            oid = ofertas().criar_oferta(db, nome='Inglês', codigo='ING-26-1', ano_letivo=2026, periodo_letivo='2026/1',
                                         disciplina_id=10, vagas=2, inscricao_aberta=True).id
            db.commit()
            ofertas().autoinscrever(db, 2, oid)
            db.commit()
            ofertas().autoinscrever(db, 7, oid)
            db.commit()
            db.add(UsuarioModel(id=9, email='tarde@example.test', senha='-', tipo='aluno'))
            db.flush()
            db.add(AlunoModel(id=9, usuario_id=9, nome='Tarde', matricula='M9'))
            db.commit()
            with self.assertRaises(MutationConflict):
                ofertas().autoinscrever(db, 9, oid)

    def test_aluno_da_oferta_ve_so_a_disciplina_da_oferta(self):
        oid = self.oferta()
        with get_session() as db:
            ofertas().matricular_aluno(db, 1, oid)
            db.commit()
        html = self.fixture.client(2).get('/estudos').get_data(as_text=True)
        self.assertIn('Robótica', html)
        self.assertNotIn('Inglês', html)

    def test_periodo_letivo_aparece_no_boletim(self):
        oid = self.oferta()
        with get_session() as db:
            ofertas().matricular_aluno(db, 1, oid)
            db.commit()
        self.assertEqual(self.fixture.client(2).get(f'/boletim?formato=json').status_code, 200)
        with get_session() as db:
            self.assertEqual(db.get(TurmaModel, oid).periodo_letivo, '2026/1')
