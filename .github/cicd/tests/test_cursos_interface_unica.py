"""B2: com o MS04 habilitado, /aprendizagem é o único caminho de cursos.

Contratos: páginas antigas redirecionam; gravações antigas respondem 410 sem efeito, também
quando o professor as envia como proposta; propostas antigas pendentes só podem ser
rejeitadas; menu aponta para /aprendizagem; cursos antigos seguem legíveis, a primeira
edição adota a versão MS04 e o progresso é preservado. Sem MS04, nada muda.
"""
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import urlsplit

from app.database import engine, get_session
from app.models import (AulaConteudoCursoModel, CursoVersaoModel, RecursoAulaCursoModel,
                        RetomadaCursoModel, SolicitacaoAlteracaoModel)
from app.models.curso_model import (AulaModel, CapituloModel, CursoModel, OfertaCursoModel,
                                    ProgressoAulaModel, TemaModel)
import test_cursos_ms04 as ms04

SEM_MS04 = 'app.services.cursos_ms04.comum.habilitado'


class InterfaceUnicaCursosTests(TestCase):
    @classmethod
    def setUpClass(cls):
        ms04.study.StudyTests.setUpClass.__func__(cls)

    setUp = ms04.CourseApiTests.setUp
    client = ms04.CourseApiTests.client
    post = ms04.CourseApiTests.post
    decide = ms04.CourseApiTests.decide
    create = ms04.CourseApiTests.create
    version = ms04.CourseApiTests.version
    edit = ms04.CourseApiTests.edit
    tree = ms04.CourseApiTests.tree
    publish = ms04.CourseApiTests.publish

    def count(self, model):
        with get_session() as db:
            return db.query(model).count()

    def destino(self, response):
        parts = urlsplit(response.location)
        return parts.path + ('?' + parts.query if parts.query else '')

    def curso_antigo(self, concluida=True):
        """Curso da interface antiga (sem versão MS04), publicado, ofertado e com progresso."""
        with get_session() as db:
            curso = CursoModel(disciplina_id=1, professor_id=1, titulo='Curso antigo', descricao='', estado='publicado')
            db.add(curso)
            db.flush()
            capitulo = CapituloModel(curso_id=curso.id, titulo='Capítulo antigo', posicao=1)
            db.add(capitulo)
            db.flush()
            tema = TemaModel(capitulo_id=capitulo.id, titulo='Tema antigo', posicao=1)
            db.add(tema)
            db.flush()
            aula = AulaModel(tema_id=tema.id, titulo='Aula em vídeo', video_id='abcdefghijk', posicao=1)
            oferta = OfertaCursoModel(curso_id=curso.id, turma_disciplina_id=1, ativa=True)
            db.add_all([aula, oferta])
            db.flush()
            if concluida:
                db.add(ProgressoAulaModel(aluno_id=1, oferta_id=oferta.id, aula_id=aula.id))
            db.commit()
            return curso.id, oferta.id, aula.id

    def test_paginas_antigas_redirecionam_para_aprendizagem(self):
        cid, offer, aula = self.curso_antigo()
        casos = [(1, '/cursos', '/aprendizagem'), (1, f'/cursos/{cid}', f'/aprendizagem/cursos/{cid}'),
                 (2, f'/aprender/{offer}', f'/aprendizagem/ofertas/{offer}'),
                 (2, f'/aprender/{offer}?aula={aula}', f'/aprendizagem/ofertas/{offer}?aula={aula}')]
        for uid, antigo, novo in casos:
            with self.subTest(antigo=antigo):
                response = self.client(uid).get(antigo)
                self.assertEqual(response.status_code, 302, response.text)
                self.assertEqual(self.destino(response), novo)
                self.assertEqual(self.client(uid).get(novo).status_code, 200)

    def test_gravacoes_antigas_respondem_410_sem_efeito(self):
        cid, offer, aula = self.curso_antigo(concluida=False)
        casos = [(1, '/cursos', {'disciplina_id': 1, 'professor_id': 1, 'titulo': 'Novo', 'descricao': ''}),
                 (1, f'/cursos/{cid}/estrutura', {'acao': 'curso', 'titulo': 'Atalho', 'descricao': ''}),
                 (1, f'/cursos/{cid}/duplicar', {}),
                 (1, f'/cursos/{cid}/estado', {'estado': 'arquivado'}),
                 (1, f'/cursos/{cid}/ofertas', {'turma_id': 1}),
                 (1, f'/cursos/ofertas/{offer}/revogar', {}),
                 (2, f'/aprender/{offer}/aulas/{aula}/concluir', {})]
        for uid, path, body in casos:
            with self.subTest(path=path):
                response = self.post(path, body, uid=uid)
                self.assertEqual(response.status_code, 410, response.text)
                self.assertIn('/aprendizagem', response.json['erro'])
        with get_session() as db:
            curso = db.get(CursoModel, cid)
            self.assertEqual((curso.titulo, curso.estado), ('Curso antigo', 'publicado'))
            self.assertTrue(db.get(OfertaCursoModel, offer).ativa)
        self.assertEqual(self.count(CursoModel), 1)
        self.assertEqual(self.count(ProgressoAulaModel), 0)

    def test_professor_nao_cria_proposta_pela_interface_antiga(self):
        response = self.post('/cursos', {'disciplina_id': 1, 'titulo': 'Proposta antiga', 'descricao': ''})
        self.assertEqual(response.status_code, 410, response.text)
        self.assertEqual(self.count(SolicitacaoAlteracaoModel), 0)
        self.assertEqual(self.count(CursoModel), 0)

    def test_proposta_antiga_pendente_so_pode_ser_rejeitada(self):
        with patch(SEM_MS04, return_value=False):
            proposal = self.post('/cursos', {'disciplina_id': 1, 'titulo': 'Proposta antiga', 'descricao': ''})
        self.assertEqual(proposal.status_code, 202, proposal.text)
        approved = self.decide(proposal.json['id'])
        self.assertEqual(approved.status_code, 410, approved.text)
        self.assertEqual(self.count(CursoModel), 0)
        self.assertEqual(self.decide(proposal.json['id'], 'rejeitar').status_code, 200)
        with get_session() as db:
            self.assertEqual(db.get(SolicitacaoAlteracaoModel, proposal.json['id']).estado, 'rejeitada')

    def test_menu_aponta_so_para_aprendizagem(self):
        for uid in (1, 2, 3):
            with self.subTest(uid=uid):
                html = self.client(uid).get('/aprendizagem').text
                self.assertIn('href="/aprendizagem"', html)
                self.assertNotIn('href="/cursos"', html)

    def test_curso_antigo_legivel_progresso_preservado_e_primeira_edicao_adota_versao(self):
        cid, offer, aula = self.curso_antigo()
        page = self.client(2).get(f'/api/aprender/{offer}')
        self.assertEqual(page.status_code, 200, page.text)
        self.assertEqual(page.json['progresso'], 100)
        self.assertEqual(self.client(2).get(f'/aprendizagem/ofertas/{offer}').status_code, 200)
        self.assertEqual(self.count(CursoVersaoModel), 0)
        # Publicado é preservado (regra do MS04): a nova edição nasce por duplicação pela API.
        copia = self.post(f'/api/cursos/{cid}/duplicar', {'versao': self.version(cid)})
        self.assertEqual(copia.status_code, 201, copia.text)
        nova = copia.json['curso_id']
        self.edit(nova, acao='curso', titulo='Curso antigo revisado', descricao='')
        with get_session() as db:
            self.assertEqual(db.get(CursoModel, cid).titulo, 'Curso antigo')
            self.assertEqual(db.get(CursoModel, nova).titulo, 'Curso antigo revisado')
        self.assertEqual(self.count(ProgressoAulaModel), 1)
        self.assertEqual(self.client(2).get(f'/api/aprender/{offer}').json['progresso'], 100)

    def test_rascunho_antigo_adota_versao_na_primeira_edicao(self):
        with get_session() as db:
            curso = CursoModel(disciplina_id=1, professor_id=1, titulo='Rascunho antigo', descricao='')
            db.add(curso)
            db.commit()
            cid = curso.id
        self.edit(cid, acao='curso', titulo='Rascunho revisado', descricao='')
        with get_session() as db:
            self.assertEqual(db.query(CursoVersaoModel).filter_by(curso_id=cid).count(), 1)
            self.assertEqual(db.get(CursoModel, cid).titulo, 'Rascunho revisado')

    def test_sem_ms04_a_interface_antiga_continua_funcionando(self):
        for model in (RecursoAulaCursoModel, RetomadaCursoModel, AulaConteudoCursoModel, CursoVersaoModel):
            model.__table__.drop(engine)
        self.assertEqual(self.client(1).get('/cursos').status_code, 200)
        created = self.post('/cursos', {'disciplina_id': 1, 'professor_id': 1, 'titulo': 'Sem MS04', 'descricao': ''}, uid=1)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertIn('href="/cursos"', self.client(1).get('/cursos').text)
