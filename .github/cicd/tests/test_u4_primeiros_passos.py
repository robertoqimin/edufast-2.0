"""U4 (plano de UX, O2): checklist "Primeiros passos" na visão geral, calculado dos dados, e telas
vazias que dizem o próximo passo."""
import json
import re
from datetime import date
from pathlib import Path
from unittest import TestCase

import test_concurrency as fixtures
import app as app_package
from app.database import get_session
from app.models import UsuarioModel
from app.models.curso_model import AtribuicaoDocenteModel, EstadoTurmaModel
from app.models.escola_model import CalendarioEscolaModel, PoliticaEscolaModel, RegraTurmaEscolaModel

APP = Path(app_package.__file__).resolve().parent
SECRETARIA, DIRECAO = 1, 9


class PrimeirosPassosTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with get_session() as db:
            db.add(UsuarioModel(id=DIRECAO, email='direcao@example.test', senha='-', tipo='super_admin'))
            db.commit()

    def html(self, user):
        client = self.app.test_client()
        with get_session() as db:
            u = db.get(UsuarioModel, user)
            with client.session_transaction() as s:
                s.update(user_id=u.id, user_role=u.tipo, user_email=u.email, auth_version=u.auth_version)
        r = client.get('/admin/dashboard')
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        return r.get_data(as_text=True)

    def passos(self, html):
        """(título, concluído?) de cada passo, na ordem da tela."""
        return [(titulo.strip(), 'passo-feito' in classe)
                for classe, titulo in re.findall(r'<li class="(passo[^"]*)"[^>]*>.*?<h3>([^<]+)', html, re.S)]

    def completar(self, turma_arquivada=False):
        with get_session() as db:
            cal = CalendarioEscolaModel(ano=2026, nome='Ano letivo 2026', inicio=date(2026, 2, 2), fim=date(2026, 12, 11))
            db.add(cal)
            db.flush()
            pol = PoliticaEscolaModel(calendario_id=cal.id, nome='Bimestres', configuracao=json.dumps({'periodos': []}))
            db.add(pol)
            db.flush()
            db.add(AtribuicaoDocenteModel(professor_id=1, turma_disciplina_id=1, ativo=True))
            db.add(RegraTurmaEscolaModel(turma_id=1, politica_id=pol.id))
            db.commit()

    def test_escola_parcial_mostra_o_proximo_passo_e_o_progresso(self):
        html = self.html(DIRECAO)
        self.assertEqual(self.passos(html), [
            ('Calendário escolar do ano', False), ('Regras do boletim', False), ('Contas da equipe', True),
            ('Disciplinas', True), ('Turmas do ano', True), ('Disciplinas e professores de cada turma', False),
            ('Alunos matriculados', True), ('Boletim aplicado às turmas', False), ('Cursos liberados para as turmas', False)])
        self.assertIn('4 de 8 concluídos', html)
        self.assertIn('<progress value="4" max="8"', html)
        self.assertRegex(html, r'(?s)passo-proximo" aria-current="step">.*?Calendário escolar do ano')
        self.assertIn('href="/super/escola">Cadastrar o calendário</a>', html)
        self.assertIn('0 de 1 turmas', html)

    def test_secretaria_ve_passos_da_direcao_sem_link(self):
        html = self.html(SECRETARIA)
        self.assertIn('A cargo da direção', html)
        self.assertNotIn('href="/super/escola"', html)
        self.assertIn('href="/admin/gestao-turmas">Atribuir professores</a>', html)

    def test_escola_completa_recolhe_o_checklist(self):
        self.completar()
        html = self.html(DIRECAO)
        self.assertIn('<details class="panel course-panel primeiros-passos primeiros-passos-concluido">', html)
        self.assertIn('Implantação concluída', html)
        self.assertIn('8 de 8 concluídos', html)
        self.assertNotIn('aria-current="step"', html)

    def test_turma_arquivada_nao_conta_e_sem_turma_nada_depende_dela(self):
        with get_session() as db:
            db.add(EstadoTurmaModel(turma_id=1, arquivada=True))
            db.commit()
        html = self.html(DIRECAO)
        passos = dict(self.passos(html))
        self.assertFalse(passos['Turmas do ano'])
        self.assertFalse(passos['Alunos matriculados'])
        self.assertIn('Crie uma turma antes', html)


# Frases com "Nenhum/Nenhuma" que não são tela vazia (regras ou avisos de segurança).
NAO_SAO_TELA_VAZIA = {
    'academico_legadas.html': 'Nenhum lançamento existente é sobrescrito',
    'academico_reconciliar.html': 'Nenhuma combinação nova é concedida automaticamente',
}
PROXIMO_PASSO = re.compile(r'Próximo passo|aparece|aparecem|aparecerão|Peça|Procure|Use |Crie|Cadastre|Associe|Registre|'
                           r'Envie|Publique|Quando |Aguarde|Comece|Lance|Matricule|Atribua|Confira|Libere|Abra|Solicite|'
                           r'Siga|Escolha|Selecione|Clique|Volte|Tente', re.I)


def telas_vazias():
    """(arquivo, linha, frase, tem_proximo_passo) de cada mensagem de tela vazia do app da escola."""
    for arquivo in sorted((APP / 'templates').glob('*.html')):
        if arquivo.name.startswith('platform_'):
            continue  # painel Supremo (outro produto, fora da escola)
        linhas = arquivo.read_text(encoding='utf-8').splitlines()
        for numero, linha in enumerate(linhas, 1):
            for achado in re.finditer(r'Nenhum[a]? [^<{]{3,}', linha):
                frase = achado.group(0)
                if NAO_SAO_TELA_VAZIA.get(arquivo.name, '\0') in frase:
                    continue
                # A orientação pode vir na mesma linha ou no parágrafo logo abaixo do título.
                trecho = (linha[achado.start():] + ' ' + ' '.join(linhas[numero:numero + 3]))[:500]
                yield arquivo.name, numero, frase, bool(PROXIMO_PASSO.search(trecho))


class TelasVaziasTests(TestCase):
    def test_toda_tela_vazia_diz_o_proximo_passo(self):
        todas = list(telas_vazias())
        self.assertGreaterEqual(len(todas), 60)   # inventário de 25/11: 66 mensagens
        sem_passo = [f'{a}:{n}: {f[:80]}' for a, n, f, ok in todas if not ok]
        self.assertEqual(sem_passo, [])
