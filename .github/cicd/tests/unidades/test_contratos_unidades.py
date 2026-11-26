"""Unidades (colégio e faculdade na mesma instalação): contratos RED. Falham até a implementação.

Pasta fora da regressão (não é pacote). Rodar à mão, com o executor isolado:
    PYTHONPATH="Codigos:.github/cicd/tests" EDUFAST_TEST_DISPOSABLE=1 \
        python -m unittest discover -s .github/cicd/tests/unidades -v
Estudo: Documentos/planejamento/ESTUDO_UNIDADES_2026-11-25.md

API esperada:
    app.models: UnidadeModel (unidades), UsuarioUnidadeModel (usuario_unidades),
        TransferenciaUnidadeModel (transferencias_unidade); TurmaModel, DisciplinaModel e
        TurmaDisciplinaModel ganham unidade_id (chaves compostas id + unidade_id).
        A unidade 1 sempre existe (a instalação atual vira a unidade 1).
    app.services.unidades:
        criar_unidade(db, *, nome, nivel) -> UnidadeModel          nivel: 'basico' | 'superior'
        vincular(db, usuario_id, unidade_id)    desvincular(db, usuario_id, unidade_id)
        escopo_banco(db, unidades)              (PostgreSQL: Row-Level Security na transação)
    HTTP:
        POST /unidade  (unidade_id = número ou 'todas'; CSRF) troca a unidade ativa;
            sessão em session['unidade_id']; sem vínculo -> 403 e nada muda.
        POST /admin/alunos/<id>/concluir  (CSRF): o colégio marca que o aluno concluiu o 3º ano.
        POST /cadastro/alunos com o CPF de um concluinte do colégio: sobe o perfil para a faculdade
            (mesma conta, histórico e documentos), sem conta nova (regra do usuário, 25/11/2026).
        POST /admin/alunos/<id>/levar-para-unidade  (destino_id; CSRF): subida manual, para aluno
            sem CPF, liberada só pela unidade de origem.
    Ficha da migration: Documentos/planejamento/PROPOSTA_010_UNIDADES_2026-11-25.md
    Recurso de outra unidade -> 404 (não confirma que existe).
"""
from unittest import TestCase, skipUnless

import test_concurrency as fixtures
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.database import engine, get_session
from app.models import (AlunoModel, AlunoTurmaModel, DisciplinaModel, ProfessorDisciplinaModel, ProfessorModel,
                        ProfessorTurmaModel, TurmaDisciplinaModel, TurmaModel, UsuarioModel)

CSRF = 'unid'
PAPEIS = {1: 'admin', 2: 'aluno', 3: 'professor', 4: 'professor', 10: 'admin', 11: 'aluno', 12: 'professor', 13: 'super_admin'}


def unidades():
    from app.services import unidades as servico  # ainda não existe: contrato RED
    return servico


def modelos():
    from app import models  # UnidadeModel, UsuarioUnidadeModel e TransferenciaUnidadeModel ainda não existem
    return models.UnidadeModel, models.UsuarioUnidadeModel, models.TransferenciaUnidadeModel


class ContratosUnidades(TestCase):
    """Colégio = unidade 1 (dados da fixture); Faculdade = unidade 2 (criada aqui).

    Colégio: admin 1, aluno 1 (usuário 2) no "3º ano B" (turma 1), Matemática; professores 1 e 2.
    Faculdade: admin 10, aluna 11 em "Engenharia — 1º semestre" (turma 21), Cálculo I (disciplina 21),
    professora 12. O professor 1 (usuário 3) dá aula nas duas. Super admin 13, sem vínculo.
    """

    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        Unidade, _, _ = modelos()
        senha = generate_password_hash('test-password-123')
        with get_session() as db:
            self.assertIsNotNone(db.get(Unidade, 1), 'a instalação atual é a unidade 1')
            faculdade = unidades().criar_unidade(db, nome='Faculdade Horizonte', nivel='superior')
            self.assertEqual(faculdade.id, 2)
            db.get(TurmaModel, 1).nome = '3º ano B'
            db.add_all([UsuarioModel(id=i, email=f'u{i}@example.test', senha=senha, tipo=PAPEIS[i]) for i in (10, 11, 12, 13)])
            db.flush()
            db.add_all([AlunoModel(id=11, usuario_id=11, nome='Aluna Faculdade', matricula='F11'),
                        ProfessorModel(id=12, usuario_id=12, nome='Professora Faculdade', cpf='33333333333'),
                        TurmaModel(id=21, nome='Engenharia — 1º semestre', codigo='ENG1', ano_letivo=2026, unidade_id=2),
                        DisciplinaModel(id=21, nome='Cálculo I', codigo='CAL1', carga_horaria=80, unidade_id=2)])
            db.flush()
            # Vínculos antes das matrículas: o banco recusa matricular quem não tem vínculo.
            for usuario, unidade in [(1, 1), (2, 1), (3, 1), (4, 1), (3, 2), (10, 2), (11, 2), (12, 2)]:
                unidades().vincular(db, usuario, unidade)
            db.add_all([TurmaDisciplinaModel(turma_id=21, disciplina_id=21, unidade_id=2),
                        AlunoTurmaModel(aluno_id=11, turma_id=21),
                        ProfessorTurmaModel(professor_id=12, turma_id=21),
                        ProfessorDisciplinaModel(professor_id=12, disciplina_id=21),
                        ProfessorTurmaModel(professor_id=1, turma_id=21),
                        ProfessorDisciplinaModel(professor_id=1, disciplina_id=21)])
            db.commit()

    # ---------- auxiliares ----------
    def cliente(self, usuario, unidade=None):
        c = self.fixture.app.test_client()
        with c.session_transaction() as s:
            s['user_id'] = usuario
            s['user_role'] = PAPEIS[usuario]
            s['user_email'] = f'u{usuario}@example.test'
            s['csrf_token'] = CSRF
            if unidade is not None:
                s['unidade_id'] = unidade
        return c

    def post(self, c, url, **dados):
        return c.post(url, data={**dados, 'csrf_token': CSRF}, headers={'X-CSRF-Token': CSRF})

    def corpo(self, c, url):
        r = c.get(url)
        self.assertEqual(r.status_code, 200, url)
        return r.get_data(as_text=True)

    def turma_do_aluno(self, aluno_id):
        with get_session() as db:
            return sorted(t for t, in db.query(AlunoTurmaModel.turma_id).filter_by(aluno_id=aluno_id))

    # ---------- 1–4: secretarias separadas ----------
    def test_01_admin_do_colegio_nao_ve_a_faculdade_nas_listas(self):
        c = self.cliente(1, unidade=1)
        for url in ('/admin/gestao-turmas', '/admin/disciplinas', '/admin/dashboard', '/admin/cadastro-alunos', '/solicitacoes'):
            html = self.corpo(c, url)
            for nome in ('Engenharia', 'Cálculo I', 'Aluna Faculdade', 'Professora Faculdade'):
                self.assertNotIn(nome, html, f'{url} mostra "{nome}" da faculdade ao admin do colégio')
        self.assertIn('3º ano B', self.corpo(c, '/admin/gestao-turmas'))
        busca = c.get('/alunos/busca?termo=Faculdade').get_json()
        self.assertNotIn('Aluna Faculdade', str(busca), 'a busca de alunos não pode atravessar a unidade')

    def test_02_admin_da_faculdade_nao_ve_o_colegio_nas_listas(self):
        c = self.cliente(10, unidade=2)
        html = self.corpo(c, '/admin/gestao-turmas')
        self.assertIn('Engenharia — 1º semestre', html)
        for nome in ('3º ano B', 'Matematica'):
            self.assertNotIn(nome, html)
        self.assertNotIn('Matematica', self.corpo(c, '/admin/disciplinas'))
        self.assertNotIn('M1', str(c.get('/alunos/busca?termo=Aluno').get_json()), 'a busca não traz o aluno do colégio')

    def test_03_recurso_de_outra_unidade_responde_404(self):
        colegio, faculdade = self.cliente(1, unidade=1), self.cliente(10, unidade=2)
        for url in ('/admin/alunos/11', '/admin/professores/12', '/academico/alunos/11/boletim'):
            self.assertEqual(colegio.get(url).status_code, 404, f'admin do colégio abriu {url}')
        for url in ('/admin/alunos/1', '/admin/professores/2', '/academico/alunos/1/boletim'):
            self.assertEqual(faculdade.get(url).status_code, 404, f'admin da faculdade abriu {url}')
        self.assertEqual(colegio.get('/admin/alunos/1').status_code, 200)

    def test_04_admin_nao_grava_na_outra_unidade(self):
        c = self.cliente(1, unidade=1)
        with get_session() as db:
            db.add(UsuarioModel(id=14, email='u14@example.test', senha='-', tipo='aluno'))
            db.flush()
            db.add(AlunoModel(id=14, usuario_id=14, nome='Calouro', matricula='F14'))
            unidades().vincular(db, 14, 2)
            db.commit()
        r = self.post(c, '/admin/gestao-turmas', acao='matricular', turma_id=21, aluno_id=14)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.turma_do_aluno(14), [])
        r = self.post(c, '/admin/gestao-turmas', acao='arquivar', turma_id=21)
        self.assertEqual(r.status_code, 404)
        with get_session() as db:
            self.assertNotEqual(getattr(db.get(TurmaModel, 21), 'status', None), 'arquivada')
        self.assertEqual(self.post(c, '/admin/alunos/11/editar', nome='Invadido').status_code, 404)
        with get_session() as db:
            self.assertEqual(db.get(AlunoModel, 11).nome, 'Aluna Faculdade')

    # ---------- 5: super admin ----------
    def test_05_super_admin_ve_todas_e_escolhe_a_unidade_para_criar(self):
        c = self.cliente(13, unidade='todas')
        html = self.corpo(c, '/admin/gestao-turmas')
        self.assertIn('3º ano B', html)
        self.assertIn('Engenharia — 1º semestre', html)
        r = self.post(c, '/admin/gestao-turmas', acao='criar', nome='Sem unidade', codigo='SU1', ano_letivo=2026)
        self.assertGreaterEqual(r.status_code, 400, 'na visão "Todas" criar exige escolher a unidade')
        self.post(c, '/admin/gestao-turmas', acao='criar', nome='Direito — 1º semestre', codigo='DIR1',
                  ano_letivo=2026, unidade_id=2)
        with get_session() as db:
            self.assertIsNone(db.query(TurmaModel).filter_by(codigo='SU1').first())
            self.assertEqual(db.query(TurmaModel).filter_by(codigo='DIR1').one().unidade_id, 2)

    # ---------- 6–8: troca de unidade e vínculo ----------
    def test_06_professor_das_duas_unidades_troca_e_ve_so_a_ativa(self):
        c = self.cliente(3)  # sem unidade na sessão: vai para a primeira do vínculo
        self.assertIn('3º ano B', self.corpo(c, '/professor/dashboard'))
        self.assertEqual(self.post(c, '/unidade', unidade_id=2).status_code, 302)
        html = self.corpo(c, '/professor/dashboard')
        self.assertIn('Engenharia — 1º semestre', html)
        self.assertNotIn('3º ano B', html)
        self.assertEqual(self.post(c, '/unidade', unidade_id=1).status_code, 302)
        self.assertNotIn('Engenharia', self.corpo(c, '/professor/dashboard'))

    def test_07_trocar_para_unidade_sem_vinculo_e_recusado(self):
        c = self.cliente(1, unidade=1)
        self.assertEqual(self.post(c, '/unidade', unidade_id=2).status_code, 403)
        with c.session_transaction() as s:
            self.assertEqual(s.get('unidade_id'), 1)
        self.assertEqual(self.post(c, '/unidade', unidade_id='todas').status_code, 403, 'só o super admin vê todas')
        forjado = self.cliente(1, unidade=2)  # sessão adulterada
        self.assertIn(forjado.get('/admin/gestao-turmas').status_code, (401, 403))
        self.assertEqual(forjado.get('/admin/alunos/11').status_code, 403)

    def test_08_revogar_o_vinculo_derruba_o_acesso_na_hora(self):
        c = self.cliente(10, unidade=2)
        self.assertEqual(c.get('/admin/gestao-turmas').status_code, 200)
        with get_session() as db:
            unidades().desvincular(db, 10, 2)
            db.commit()
        self.assertIn(c.get('/admin/gestao-turmas').status_code, (401, 403))

    # ---------- 9–10: garantias no banco ----------
    def test_09_banco_recusa_ligar_turma_e_disciplina_de_unidades_diferentes(self):
        for unidade in (1, 2):
            with get_session() as db:
                db.add(TurmaDisciplinaModel(turma_id=1, disciplina_id=21, unidade_id=unidade))
                with self.assertRaises(IntegrityError, msg=f'turma do colégio + Cálculo I (unidade_id={unidade})'):
                    db.commit()
                db.rollback()
        with get_session() as db:
            db.add(AlunoTurmaModel(aluno_id=1, turma_id=21))
            with self.assertRaises(IntegrityError, msg='aluno sem vínculo com a faculdade numa turma da faculdade'):
                db.commit()

    @skipUnless(fixtures.REAL_DB, 'Row-Level Security só existe no PostgreSQL')
    def test_10_row_level_security_esconde_a_outra_unidade_mesmo_sem_filtro(self):
        with get_session() as db:
            with unidades().escopo_banco(db, [1]):
                nomes = [n for n, in db.execute(text('SELECT nome FROM turmas'))]
            self.assertIn('3º ano B', nomes)
            self.assertNotIn('Engenharia — 1º semestre', nomes)
            with unidades().escopo_banco(db, [1]):
                self.assertEqual(db.execute(text('SELECT count(*) FROM disciplinas WHERE id = 21')).scalar(), 0)

    # ---------- 11: professor que já existe na outra unidade ----------
    def test_11_cadastrar_professor_com_cpf_existente_so_vincula(self):
        c = self.cliente(10, unidade=2)
        r = c.post('/cadastro/professores', json={'nome': 'Professor 2', 'email': 'outro@example.test',
                                                  'senha': 'test-password-123', 'cpf': '22222222222'},
                   headers={'X-CSRF-Token': CSRF})
        self.assertIn(r.status_code, (200, 201))
        texto = r.get_data(as_text=True)
        for dado_do_colegio in ('u4@example.test', '3º ano B', 'Matematica'):
            self.assertNotIn(dado_do_colegio, texto, 'a resposta não pode expor dados do colégio')
        _, Vinculo, _ = modelos()
        with get_session() as db:
            self.assertIsNone(db.query(UsuarioModel).filter_by(email='outro@example.test').first(), 'nenhuma conta nova')
            self.assertTrue(db.query(Vinculo).filter_by(usuario_id=4, unidade_id=2).first(), 'mesmo login nas duas')

    # ---------- 12–14: subida do colégio para a faculdade pelo CPF (regra do usuário) ----------
    CPF = '52998224725'

    def preparar_cpf(self):
        with get_session() as db:
            db.get(AlunoModel, 1).cpf = self.CPF
            db.commit()

    def cadastrar_na_faculdade(self, cpf):
        return self.cliente(10, unidade=2).post('/cadastro/alunos', json={
            'nome': 'Aluno', 'email': 'calouro@example.test', 'senha': 'test-password-123',
            'matricula': 'F2', 'cpf': cpf}, headers={'X-CSRF-Token': CSRF})

    def test_12_concluinte_do_3o_ano_sobe_para_a_faculdade_pelo_cpf(self):
        self.preparar_cpf()
        faculdade = self.cliente(10, unidade=2)
        self.assertEqual(faculdade.get('/admin/alunos/1').status_code, 404, 'antes da subida a faculdade não vê')
        self.assertEqual(self.post(self.cliente(1, unidade=1), '/admin/alunos/1/concluir').status_code, 302)
        r = self.cadastrar_na_faculdade(self.CPF)
        self.assertIn(r.status_code, (200, 201))
        _, Vinculo, Transferencia = modelos()
        with get_session() as db:
            self.assertIsNone(db.query(UsuarioModel).filter_by(email='calouro@example.test').first(), 'sem conta nova')
            self.assertEqual(db.query(AlunoModel).filter_by(cpf=self.CPF).count(), 1, 'um cadastro só')
            self.assertEqual(db.query(Vinculo).filter_by(usuario_id=2, unidade_id=1).one().situacao, 'concluido')
            self.assertEqual(db.query(Vinculo).filter_by(usuario_id=2, unidade_id=2).one().situacao, 'ativo')
            t = db.query(Transferencia).one()
            self.assertEqual((t.aluno_id, t.origem_id, t.destino_id, t.autor_id, t.motivo), (1, 1, 2, 10, 'cpf_concluinte'))
        self.assertIn('RG', self.corpo(faculdade, '/admin/alunos/1'), 'documentos do colégio sobem junto')
        self.assertEqual(faculdade.get('/academico/alunos/1/boletim').status_code, 200, 'histórico escolar do colégio')
        aluno = self.cliente(2)  # o mesmo login do colégio
        self.assertEqual(self.post(aluno, '/unidade', unidade_id=2).status_code, 302)
        self.assertEqual(self.turma_do_aluno(1), [1], 'a subida não matricula sozinha em turma da faculdade')

    def test_13_cpf_de_quem_nao_concluiu_e_recusado_sem_expor_dados(self):
        self.preparar_cpf()
        r = self.cadastrar_na_faculdade(self.CPF)
        self.assertEqual(r.status_code, 409)
        texto = r.get_data(as_text=True)
        self.assertIn('ainda não concluiu', r.get_json()['erro'])
        for dado_do_colegio in ('M1', '3º ano B', 'u2@example.test'):
            self.assertNotIn(dado_do_colegio, texto)
        # Só o colégio marca "concluiu"; a faculdade e o professor não podem.
        self.assertEqual(self.post(self.cliente(10, unidade=2), '/admin/alunos/1/concluir').status_code, 404)
        self.assertEqual(self.post(self.cliente(3, unidade=1), '/admin/alunos/1/concluir').status_code, 403)
        _, Vinculo, Transferencia = modelos()
        with get_session() as db:
            self.assertIsNone(db.query(Vinculo).filter_by(usuario_id=2, unidade_id=2).first())
            self.assertEqual(db.query(Transferencia).count(), 0)

    def test_14_subida_nao_se_repete_e_aluno_sem_cpf_sobe_pelo_colegio(self):
        self.preparar_cpf()
        self.post(self.cliente(1, unidade=1), '/admin/alunos/1/concluir')
        self.assertIn(self.cadastrar_na_faculdade(self.CPF).status_code, (200, 201))
        r = self.cadastrar_na_faculdade(self.CPF)
        self.assertEqual(r.status_code, 409)
        self.assertIn('já está na faculdade', r.get_json()['erro'])
        # Aluno sem CPF: a secretaria do colégio libera manualmente; a faculdade não puxa sozinha.
        with get_session() as db:
            db.add(UsuarioModel(id=15, email='u15@example.test', senha='-', tipo='aluno'))
            db.flush()
            db.add(AlunoModel(id=15, usuario_id=15, nome='Sem CPF', matricula='M15'))
            unidades().vincular(db, 15, 1)
            db.commit()
        self.assertEqual(self.post(self.cliente(10, unidade=2), '/admin/alunos/15/levar-para-unidade', destino_id=2).status_code, 404)
        self.assertEqual(self.post(self.cliente(1, unidade=1), '/admin/alunos/15/levar-para-unidade', destino_id=2).status_code, 302)
        _, _, Transferencia = modelos()
        with get_session() as db:
            self.assertEqual(sorted((t.aluno_id, t.motivo) for t in db.query(Transferencia)), [(1, 'cpf_concluinte'), (15, 'manual')])

    # ---------- 15: aprovações separadas por unidade ----------
    def test_15_secretaria_so_ve_e_decide_solicitacoes_da_propria_unidade(self):
        import json
        from app.models import SolicitacaoAlteracaoModel
        with get_session() as db:
            db.add(SolicitacaoAlteracaoModel(id=50, solicitante_id=12, tipo='cadastro', estado='pendente', unidade_id=2,
                                             payload=json.dumps({'usuario_id': 12, 'papel_solicitado': 'professor'}),
                                             recurso_pendente='cadastro:12'))
            db.commit()
        colegio, faculdade = self.cliente(1, unidade=1), self.cliente(10, unidade=2)
        self.assertNotIn('Solicitação 50', self.corpo(colegio, '/solicitacoes?estado=todas'))
        self.assertIn('Solicitação 50', self.corpo(faculdade, '/solicitacoes?estado=todas'))
        r = self.post(colegio, '/solicitacoes/alteracoes/50/decidir', decisao='rejeitar', justificativa='x')
        self.assertEqual(r.status_code, 404)
        with get_session() as db:
            self.assertEqual(db.get(SolicitacaoAlteracaoModel, 50).estado, 'pendente')
