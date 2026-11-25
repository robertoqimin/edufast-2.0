"""U3 (plano de UX, O1): a avaliação inteira vira UMA solicitação; a secretaria vê o resumo e
aprova (ou rejeita) várias solicitações de uma vez. Aplicação tudo-ou-nada e auditoria preservadas."""
from unittest import TestCase

import test_notas_unificadas as b1
from app.database import get_session
from app.models import AlunoModel, AlunoTurmaModel, SolicitacaoAlteracaoModel, UsuarioModel
from app.models.academico_model import AuditoriaAcademicaModel, AvaliacaoModel, LancamentoNotaModel

PROFESSOR, SECRETARIA = 3, 1


class LoteTests(TestCase):
    setUpClass = classmethod(lambda cls: b1.NotasUnificadasTests.setUpClass.__func__(cls))
    setUp = b1.NotasUnificadasTests.setUp
    client = b1.NotasUnificadasTests.client
    post_json = b1.NotasUnificadasTests.post_json
    decide = b1.NotasUnificadasTests.decide
    html = b1.NotasUnificadasTests.html

    def preparar(self, nota=None):
        b1.NotasUnificadasTests.preparar_diario(self, nota=nota)
        with get_session() as db:
            for i, nome in ((3, 'Bruna Alves'), (4, 'Caio Dias')):
                db.add(UsuarioModel(id=20 + i, email=f'aluno{i}@example.test', senha='-', tipo='aluno'))
                db.flush()
                db.add(AlunoModel(id=i, usuario_id=20 + i, nome=nome, matricula=f'M{i}'))
                db.flush()
                db.add(AlunoTurmaModel(aluno_id=i, turma_id=1))
            db.add(AvaliacaoModel(id=2, turma_disciplina_id=1, periodo_id=1, titulo='Trabalho B1', peso=1))
            db.commit()

    def lote(self, avaliacao=1, **campos):
        return self.post_json(f'/academico/avaliacoes/{avaliacao}/lancamentos', campos, user=PROFESSOR)

    def notas(self, avaliacao=1):
        with get_session() as db:
            return {n.aluno_id: str(n.valor) for n in db.query(LancamentoNotaModel).filter_by(avaliacao_id=avaliacao)}

    def pendentes(self):
        with get_session() as db:
            return db.query(SolicitacaoAlteracaoModel).filter_by(estado='pendente').all()

    def test_avaliacao_inteira_vira_uma_solicitacao_e_entra_de_uma_vez(self):
        self.preparar()
        r = self.lote(valor_1='8', versao_1='0', valor_3='6,5', versao_3='0', observacao_3='Refazer a questão 2',
                      valor_4='', versao_4='0')
        self.assertEqual(r.status_code, 202, r.get_data(as_text=True))
        pendentes = self.pendentes()
        self.assertEqual(len(pendentes), 1)
        self.assertEqual(pendentes[0].recurso_pendente, 'notas:1')
        self.assertEqual(self.notas(), {})                                   # nada antes da aprovação
        diario = self.html('/academico/avaliacoes/1', PROFESSOR)
        self.assertIn('aguardam aprovação da secretaria (2 notas)', diario)
        self.assertIn('Aguardando aprovação: 6,5', diario)
        self.assertNotIn('Enviar notas para aprovação', diario)            # outro envio só depois da decisão
        self.assertIn('2 aguardando aprovação', self.html('/professor/dashboard', PROFESSOR))
        self.assertEqual(self.lote(valor_1='9', versao_1='0').status_code, 409)   # uma pendente por avaliação
        self.assertEqual(self.decide(r.json['id']).status_code, 200)
        self.assertEqual(self.notas(), {1: '8.00', 3: '6.50'})            # aluno 4 segue pendente
        with get_session() as db:
            acoes = [a for a, in db.query(AuditoriaAcademicaModel.acao).order_by(AuditoriaAcademicaModel.id)]
        self.assertEqual(acoes.count('salvar_nota'), 2)
        self.assertIn('salvar_notas_lote', acoes)
        self.assertIn('Enviar notas para aprovação', self.html('/academico/avaliacoes/1', PROFESSOR))

    def test_so_notas_novas_ou_alteradas_entram(self):
        self.preparar(nota='7.5')
        self.assertEqual(self.lote(valor_1='7,50', versao_1='1').status_code, 400)        # nada mudou
        r = self.lote(valor_1='7.5', versao_1='1', valor_3='9', versao_3='0')
        self.assertEqual(r.status_code, 202)
        self.decide(r.json['id'])
        with get_session() as db:
            self.assertEqual(db.query(LancamentoNotaModel).filter_by(aluno_id=1).one().versao, 1)  # sem nova versão

    def test_campos_e_valores_invalidos_sao_recusados_no_envio(self):
        self.preparar()
        for campos in ({'aluno_id': '1'}, {'valor_x': '8'}, {'valor_1': '11', 'versao_1': '0'},
                       {'valor_1': '8', 'versao_1': '0', 'valor_99': '7', 'versao_99': '0'}):
            with self.subTest(campos=campos):
                self.assertGreaterEqual(self.lote(**campos).status_code, 400)
        self.assertEqual(self.pendentes(), [])

    def test_aplicacao_e_tudo_ou_nada_quando_o_diario_mudou(self):
        self.preparar()
        lote = self.lote(valor_1='8', versao_1='0', valor_3='6', versao_3='0')
        individual = self.post_json('/academico/avaliacoes/1/alunos/1', {'valor': '5', 'versao': 0}, user=PROFESSOR)
        self.assertEqual(self.decide(individual.json['id']).status_code, 200)
        r = self.decide(lote.json['id'])
        self.assertEqual(r.status_code, 409, r.get_data(as_text=True))
        self.assertEqual(self.notas(), {1: '5.00'})                         # nada do lote entrou (nem a do aluno 3)

    def test_secretaria_ve_resumo_do_lote(self):
        self.preparar(nota='4')
        self.lote(valor_1='6', versao_1='1', valor_3='9,25', versao_3='0')
        html = self.html('/solicitacoes', SECRETARIA)
        self.assertIn('Lançar notas da avaliação', html)
        self.assertIn('2 (1 novas, 1 alteradas)', html)
        self.assertIn('<th scope="row">Bruna Alves</th><td>—</td><td><strong>9,25</strong>', html)
        self.assertIn('<td>4,00</td><td><strong>6</strong></td><td>Alterada</td>', html)
        self.assertIn('Abrir o diário da avaliação', html)

    def test_secretaria_aprova_varias_de_uma_vez_e_ve_o_que_falhou(self):
        self.preparar()
        a = self.lote(1, valor_1='8', versao_1='0').json['id']
        b = self.lote(2, valor_1='7', versao_1='0').json['id']
        self.assertIn('Aprovar selecionadas', self.html('/solicitacoes', SECRETARIA))
        r = self.client(SECRETARIA).post('/solicitacoes/alteracoes/lote', data={
            'ids': [str(a), str(b), '9999'], 'decisao': 'aprovar', 'csrf_token': b1.CSRF},
            headers={'Accept': 'application/json'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json['decididas'], [a, b])
        self.assertEqual([f['id'] for f in r.json['falhas']], [9999])
        self.assertEqual((self.notas(1), self.notas(2)), ({1: '8.00'}, {1: '7.00'}))
        decididas = self.html('/solicitacoes', SECRETARIA)
        self.assertIn('Lançar notas da avaliação', decididas)
        self.assertNotIn('Nota enviada', decididas)        # sem comparação enganosa depois da decisão
        self.assertNotIn('Aprovar selecionadas', decididas)

    def test_lote_respeita_permissao_e_rejeicao(self):
        self.preparar()
        a = self.lote(valor_1='8', versao_1='0').json['id']
        proprio = self.post_json('/solicitacoes/alteracoes/lote', {'ids': [a], 'decisao': 'aprovar'}, user=PROFESSOR)
        self.assertEqual(proprio.json['falhas'][0]['id'], a)                 # quem envia não aprova
        self.assertEqual(self.post_json('/solicitacoes/alteracoes/lote', {'ids': [], 'decisao': 'aprovar'}).status_code, 400)
        r = self.post_json('/solicitacoes/alteracoes/lote', {'ids': [a], 'decisao': 'rejeitar', 'justificativa': 'Rever a prova'})
        self.assertEqual(r.json['decididas'], [a])
        self.assertEqual(self.notas(), {})
        with get_session() as db:
            self.assertEqual(db.get(SolicitacaoAlteracaoModel, a).justificativa, 'Rever a prova')
        self.assertIn('Enviar notas para aprovação', self.html('/academico/avaliacoes/1', PROFESSOR))

    def test_diario_tem_um_formulario_para_a_turma_inteira(self):
        self.preparar()
        html = self.html('/academico/avaliacoes/1', PROFESSOR)
        self.assertEqual(html.count('action="/academico/avaliacoes/1/lancamentos"'), 1)
        for aluno in (1, 3, 4):
            self.assertIn(f'name="valor_{aluno}"', html)
        self.assertIn('aria-label="Nota de Bruna Alves"', html)
        self.assertNotIn('/academico/avaliacoes/1/alunos/', html)
