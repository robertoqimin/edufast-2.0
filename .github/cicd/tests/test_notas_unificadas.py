"""B1: o módulo acadêmico é a única fonte de notas nas telas.

Contratos: o painel antigo não grava mais em `notas`; o professor lança pelo diário,
com aprovação por ação; o aluno vê só avaliações publicadas; notas antigas ficam
preservadas para reconciliação e nunca são apagadas.
"""
import json
import re
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

import test_concurrency as fixtures
import app as app_package
from app.database import get_session
from app.models import NotaModel, SolicitacaoAlteracaoModel
from app.models.academico_model import AvaliacaoModel, LancamentoNotaModel, PeriodoLetivoModel
from app.models.curso_model import AtribuicaoDocenteModel, EstadoTurmaModel

# Localiza o pacote pelo import: no repositório é api/app; na imagem de produção, /app/app.
APP = Path(app_package.__file__).resolve().parent
CSRF = 'csrf-b1'


class NotasUnificadasTests(TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MutationApiTests.setUpClass()
        cls.app = fixtures.MutationApiTests.app

    def setUp(self):
        self.fixture = fixtures.MutationApiTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def client(self, user=1):
        client = self.fixture.client(user)
        with client.session_transaction() as session:
            session['csrf_token'] = CSRF
        return client

    def post_json(self, path, body, user=1):
        return self.client(user).post(path, json=body, headers={'X-CSRF-Token': CSRF, 'Idempotency-Key': uuid4().hex})

    def decide(self, proposal_id, decision='aprovar'):
        return self.post_json(f'/solicitacoes/alteracoes/{proposal_id}/decidir', {'decisao': decision})

    def count(self, model):
        return self.fixture.count(model)

    def preparar_diario(self, publicada=False, nota=None):
        with get_session() as db:
            db.add(AtribuicaoDocenteModel(professor_id=1, turma_disciplina_id=1, ativo=True))
            db.add(EstadoTurmaModel(turma_id=1, arquivada=False))
            db.add(PeriodoLetivoModel(id=1, turma_id=1, nome='Primeiro bimestre', ordem=1))
            db.flush()
            db.add(AvaliacaoModel(id=1, turma_disciplina_id=1, periodo_id=1, titulo='Prova B1', peso=1, publicada=publicada))
            if nota is not None:
                db.flush()
                db.add(LancamentoNotaModel(avaliacao_id=1, aluno_id=1, professor_id=1, valor=nota, observacao='', versao=1))
            db.commit()

    def nota_antiga(self, valor='4.25'):
        with get_session() as db:
            db.add(NotaModel(aluno_id=1, disciplina_id=1, professor_id=1, nota=valor, observacao='Registro anterior'))
            db.commit()

    def html(self, path, user):
        response = self.client(user).get(path)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:300])
        return response.get_data(as_text=True)

    # Painel antigo aposentado

    def test_rota_antiga_de_nota_foi_aposentada(self):
        data = {**self.fixture.grade(), 'csrf_token': CSRF}
        response = self.client(3).post('/professor/notas/salvar', data=data)
        self.assertEqual(response.status_code, 410, response.get_data(as_text=True))
        self.assertIn('/academico', response.json['destino'])
        self.assertEqual(self.count(NotaModel), 0)
        self.assertEqual(self.count(SolicitacaoAlteracaoModel), 0)

    def test_api_nao_aceita_nova_proposta_de_nota_antiga(self):
        grade = {k: v for k, v in self.fixture.grade().items() if k != 'idempotency_key'}
        response = self.post_json('/solicitacoes/alteracoes', {'tipo': 'salvar_nota', 'payload': grade}, user=3)
        self.assertEqual(response.status_code, 410, response.get_data(as_text=True))
        self.assertEqual(self.count(SolicitacaoAlteracaoModel), 0)

    def test_proposta_antiga_pendente_so_pode_ser_rejeitada(self):
        payload = {'aluno_id': 1, 'turma_id': 1, 'disciplina_id': 1, 'nota': '8', 'observacao': '', 'versao': 0}
        with get_session() as db:
            row = SolicitacaoAlteracaoModel(solicitante_id=3, tipo='salvar_nota', payload=json.dumps(payload),
                                            estado='pendente', recurso_pendente='nota:1:1:0')
            db.add(row)
            db.commit()
            proposal_id = row.id
        listing = self.client().get('/solicitacoes/alteracoes').json['solicitacoes']
        self.assertIn('diário', listing[0]['titulo'])
        approved = self.decide(proposal_id)
        self.assertEqual(approved.status_code, 409, approved.get_data(as_text=True))
        self.assertEqual(self.count(NotaModel), 0)
        self.assertEqual(self.decide(proposal_id, 'rejeitar').status_code, 200)
        with get_session() as db:
            self.assertEqual(db.get(SolicitacaoAlteracaoModel, proposal_id).estado, 'rejeitada')

    def test_nenhum_codigo_da_aplicacao_grava_na_tabela_antiga(self):
        writes = re.compile(r'(?<!Lancamento)NotaModel\(|(insert|update|delete)\(\s*NotaModel\b'
                            r'|query\(\s*NotaModel\b[^#]*\.(update|delete)\(')
        found = []
        arquivos = list(APP.rglob('*.py'))
        self.assertGreater(len(arquivos), 30, f'varredura vazia em {APP}')
        self.assertTrue((APP / 'services' / 'aprovacoes_service.py').exists())
        for path in arquivos:
            if path.name == 'nota_model.py':
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if writes.search(line):
                    found.append(f'{path.relative_to(APP)}:{number}: {line.strip()}')
        self.assertEqual(found, [])

    # Professor

    def test_painel_do_professor_leva_ao_diario(self):
        self.preparar_diario()
        html = self.html('/professor/dashboard', 3)
        self.assertNotIn('/professor/notas/salvar', html)
        self.assertNotIn('professor-grade-form', html)
        self.assertIn('/academico/avaliacoes/1', html)
        self.assertIn('Prova B1', html)
        self.assertIn('Rascunho', html)

    def test_painel_do_professor_explica_quando_falta_atribuicao(self):
        html = self.html('/professor/dashboard', 3)
        self.assertNotIn('/professor/notas/salvar', html)
        self.assertIn('Aguardando a secretaria confirmar', html)

    def test_painel_do_professor_respeita_atribuicao_revogada(self):
        self.preparar_diario(nota='9.25')
        self.assertIn('9.25', self.html('/professor/dashboard', 3))
        with get_session() as db:
            db.query(AtribuicaoDocenteModel).update({'ativo': False})
            db.commit()
        html = self.html('/professor/dashboard', 3)
        self.assertNotIn('9.25', html)
        self.assertNotIn('Prova B1', html)

    def test_painel_do_professor_mostra_lancamento_aguardando_aprovacao(self):
        self.preparar_diario()
        proposal = self.post_json('/academico/avaliacoes/1/alunos/1', {'valor': '8', 'versao': 0}, user=3)
        self.assertEqual(proposal.status_code, 202, proposal.get_data(as_text=True))
        html = self.html('/professor/dashboard', 3)
        self.assertIn('1 aguardando aprovação', html)

    def test_professor_lanca_pelo_diario_somente_com_aprovacao(self):
        self.preparar_diario()
        proposal = self.post_json('/academico/avaliacoes/1/alunos/1', {'valor': '8', 'versao': 0}, user=3)
        self.assertEqual(proposal.status_code, 202, proposal.get_data(as_text=True))
        self.assertEqual(self.count(LancamentoNotaModel), 0)
        self.assertEqual(self.decide(proposal.json['id']).status_code, 200)
        stale = self.post_json('/academico/avaliacoes/1/alunos/1', {'valor': '3', 'versao': 0}, user=3)
        self.assertEqual(stale.status_code, 409, stale.get_data(as_text=True))
        with get_session() as db:
            self.assertEqual(str(db.query(LancamentoNotaModel).one().valor), '8.00')
        self.assertEqual(self.count(NotaModel), 0)

    # Aluno

    def test_aluno_ve_apenas_avaliacao_publicada(self):
        self.preparar_diario(publicada=False, nota='7.5')
        self.assertNotIn('7.50', self.html('/aluno/dashboard', 2))
        with get_session() as db:
            db.get(AvaliacaoModel, 1).publicada = True
            db.commit()
        html = self.html('/aluno/dashboard', 2)
        self.assertIn('7.50', html)
        self.assertIn('Primeiro bimestre', html)
        self.assertIn('/boletim', html)

    def test_nota_antiga_nao_aparece_como_nota_atual_do_aluno(self):
        self.nota_antiga('4.25')
        html = self.html('/aluno/dashboard', 2)
        self.assertNotIn('4.25', html)
        self.assertIn('registros anteriores', html)
        self.assertIn('4.25', self.html('/boletim', 2))

    # Secretaria

    def test_notas_antigas_continuam_para_reconciliacao(self):
        self.preparar_diario()
        self.nota_antiga('6.75')
        self.assertIn('6.75', self.html('/academico/notas-antigas', 1))
        with get_session() as db:
            legacy = db.query(NotaModel).one()
            legacy_id, valor = legacy.id, str(legacy.nota)
        linked = self.post_json(f'/academico/notas-antigas/{legacy_id}/vincular', {'avaliacao_id': 1, 'valor_confirmado': valor})
        self.assertEqual(linked.status_code, 200, linked.get_data(as_text=True))
        with get_session() as db:
            self.assertEqual(db.query(LancamentoNotaModel).one().nota_legada_id, legacy_id)
            self.assertEqual(str(db.query(NotaModel).one().nota), '6.75')

    def test_detalhe_do_professor_mostra_notas_do_diario(self):
        self.preparar_diario(nota='9.25')
        self.nota_antiga('1.50')
        html = self.html('/admin/professores/1', 1)
        self.assertIn('9.25', html)
        self.assertIn('Prova B1', html)
        self.assertNotIn('1.50', html)
