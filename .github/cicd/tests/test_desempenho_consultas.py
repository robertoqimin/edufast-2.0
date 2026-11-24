"""B3/MS05: guardas de regressão de desempenho determinísticas (contagem de consultas).

O número de consultas das páginas corrigidas não pode crescer com o tamanho da escola, e as
versões em lote preservam exatamente as regras de acesso e os resultados.
"""
from contextlib import contextmanager
from unittest import TestCase

from sqlalchemy import event

import test_concurrency as fixtures
from app.database import engine, get_session
from app.models import (AlunoTurmaModel, DisciplinaModel, ProfessorDisciplinaModel, ProfessorTurmaModel,
                        TurmaDisciplinaModel, TurmaModel)
from app.models.academico_model import AvaliacaoModel, LancamentoNotaModel, PeriodoLetivoModel
from app.models.curso_model import AtribuicaoDocenteModel, EstadoTurmaModel
from app.services import frequencia_service
from app.services.identidade_service import Identidade


@contextmanager
def contar_consultas():
    total = {'n': 0}

    def contar(*_):
        total['n'] += 1
    event.listen(engine, 'before_cursor_execute', contar)
    try:
        yield total
    finally:
        event.remove(engine, 'before_cursor_execute', contar)


class DesempenhoConsultasTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def ampliar(self, turmas, disciplinas, periodos=2):
        """Escola maior: turmas × disciplinas, professor 1 atribuído a todas, notas do aluno 1 em todas."""
        with get_session() as db:
            for d in range(2, disciplinas + 1):
                db.add(DisciplinaModel(id=d, nome=f'Disciplina {d}', codigo=f'D{d}', carga_horaria=40))
                db.add(ProfessorDisciplinaModel(professor_id=1, disciplina_id=d))
            for t in range(2, turmas + 1):
                db.add(TurmaModel(id=t, nome=f'Turma {t}', codigo=f'T{t}', ano_letivo=2026))
                db.add(ProfessorTurmaModel(professor_id=1, turma_id=t))
            db.flush()
            vinculos = []
            for t in range(1, turmas + 1):
                for d in range(1, disciplinas + 1):
                    if (t, d) != (1, 1):
                        db.add(TurmaDisciplinaModel(id=t * 100 + d, turma_id=t, disciplina_id=d))
            db.flush()
            vinculos = db.query(TurmaDisciplinaModel).all()
            for v in vinculos:
                db.add(AtribuicaoDocenteModel(professor_id=1, turma_disciplina_id=v.id, ativo=True))
            for t in range(1, turmas + 1):
                db.add(EstadoTurmaModel(turma_id=t, arquivada=False))
                for o in range(1, periodos + 1):
                    db.add(PeriodoLetivoModel(id=t * 10 + o, turma_id=t, nome=f'{o}º período', ordem=o))
            db.flush()
            for v in vinculos:
                if v.turma_id != 1:
                    continue
                for o in range(1, periodos + 1):
                    av = AvaliacaoModel(turma_disciplina_id=v.id, periodo_id=10 + o, titulo=f'Prova {o}', peso=1, publicada=True)
                    db.add(av)
                    db.flush()
                    db.add(LancamentoNotaModel(avaliacao_id=av.id, aluno_id=1, professor_id=1, valor='7.50', versao=1))
            db.commit()

    def consultas(self, path, user):
        client = self.fixture.client(user)
        client.get(path)  # aquecimento (caches de sessão/identidade)
        with contar_consultas() as total:
            response = client.get(path)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:300])
        return total['n'], response.get_data(as_text=True)

    def test_regra_em_lote_igual_a_regra_individual(self):
        self.ampliar(turmas=3, disciplinas=2)
        with get_session() as db:
            db.query(AtribuicaoDocenteModel).filter_by(turma_disciplina_id=201).update({'ativo': False})
            db.query(AtribuicaoDocenteModel).filter_by(turma_disciplina_id=302).update({'professor_id': 2})
            db.query(AtribuicaoDocenteModel).filter_by(turma_disciplina_id=301).delete()  # cai na regra antiga
            db.commit()
            pairs = db.query(TurmaDisciplinaModel).all()
            for identidade in [Identidade(3, 'professor', False, 0), Identidade(4, 'professor', False, 0),
                               Identidade(1, 'admin', False, 0), Identidade(2, 'aluno', False, 0)]:
                individuais = set()
                for pair in pairs:
                    try:
                        frequencia_service.scope(db, identidade, pair.id)
                        individuais.add(pair.id)
                    except frequencia_service.MutationConflict:
                        pass
                with self.subTest(papel=identidade.papel, usuario=identidade.id):
                    self.assertEqual(frequencia_service.pares_permitidos(db, identidade, pairs), individuais)

    def test_painel_de_frequencia_nao_cresce_com_a_escola(self):
        pequena, _ = self.consultas('/frequencia', 3)
        self.ampliar(turmas=6, disciplinas=4)
        grande, html = self.consultas('/frequencia', 3)
        self.assertIn('Turma 6', html)
        self.assertLessEqual(grande, pequena + 2, (pequena, grande))

    def test_boletim_nao_cresce_com_periodos_e_disciplinas(self):
        self.ampliar(turmas=1, disciplinas=1, periodos=1)
        pequeno, _ = self.consultas('/boletim', 2)
        with get_session() as db:
            for d in range(2, 5):
                db.add(DisciplinaModel(id=d, nome=f'Disciplina {d}', codigo=f'D{d}', carga_horaria=40))
                db.add(TurmaDisciplinaModel(id=100 + d, turma_id=1, disciplina_id=d))
            for o in range(2, 5):
                db.add(PeriodoLetivoModel(id=10 + o, turma_id=1, nome=f'{o}º período', ordem=o))
            db.flush()
            for v in db.query(TurmaDisciplinaModel).all():
                for o in range(1, 5):
                    if (v.id, o) == (1, 1):
                        continue
                    av = AvaliacaoModel(turma_disciplina_id=v.id, periodo_id=10 + o, titulo=f'P{o}', peso=1, publicada=True)
                    db.add(av)
                    db.flush()
                    db.add(LancamentoNotaModel(avaliacao_id=av.id, aluno_id=1, professor_id=1, valor='8.00', versao=1))
            db.commit()
        grande, html = self.consultas('/boletim', 2)
        self.assertEqual(html.count('Média ponderada: 8.00'), 15)
        self.assertLessEqual(grande, pequeno + 2, (pequeno, grande))

    def test_academico_da_secretaria_mostra_uma_turma_por_vez(self):
        self.ampliar(turmas=3, disciplinas=2)
        _, html = self.consultas('/academico', 1)
        self.assertIn('Turma exibida', html)
        self.assertIn('/academico/avaliacoes/', html)
        self.assertNotIn('Turma 2 </span>', html)
        _, segunda = self.consultas('/academico?turma=2', 1)
        self.assertIn('2026 · Turma 2', segunda)
        self.assertNotIn('2026 · Turma 3', segunda)
        _, professor = self.consultas('/academico', 3)
        for turma in ('Turma 2', 'Turma 3'):
            self.assertIn('2026 · ' + turma, professor)
        self.assertIn('Todas as minhas turmas', professor)
