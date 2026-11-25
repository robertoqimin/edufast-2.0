"""U2 (plano de UX, O7): estudar sem baixar — leitor de PDF local, imagem, vídeo, anterior/próximo e visto."""
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

import test_cursos_ms04 as ms04
import test_estudos as study
import app as app_package
from app.database import get_session
from app.models import AuditoriaEstudoModel
from app.models.curso_model import AuditoriaCursoModel

APP = Path(app_package.__file__).resolve().parent
VENDOR = APP / 'static/vendor/pdfjs'


def emprestar(origem, *nomes):
    """Usa os auxiliares de outra suíte sem herdar (e repetir) os testes dela."""
    return {n: getattr(origem, n) for n in nomes}


class LeitorEstudoTests(TestCase):
    setUpClass = classmethod(lambda cls: study.StudyTests.setUpClass.__func__(cls))
    locals().update(emprestar(study.StudyTests, 'setUp', 'client', 'post', 'create', 'upload', 'propose', 'decide', 'publish'))

    def material(self, **values):
        rid = self.create(**values).json['id']
        self.publish(rid)
        return rid

    def arquivo(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.text)
        self.publish(response.json['id'])
        return response.json['id']

    def acoes(self, rid, uid=2):
        with get_session() as db:
            return [a for a, in db.query(AuditoriaEstudoModel.acao).filter_by(conteudo_id=rid, ator_id=uid).order_by(AuditoriaEstudoModel.id)]

    def test_pdf_abre_no_leitor_e_baixar_fica_opcional(self):
        rid = self.arquivo()
        html = self.client(2).get(f'/estudos/conteudos/{rid}').get_data(as_text=True)
        self.assertIn('data-leitor="pdf"', html)
        self.assertIn(f'data-src="/estudos/conteudos/{rid}/arquivo?modo=ler"', html)
        self.assertIn('js/paginas/leitor_material.js', html)
        self.assertIn('Baixar uma cópia', html)
        self.assertNotIn('button-primary" href="/estudos/conteudos', html)  # baixar deixou de ser a ação principal

    def test_leitura_continua_privada_cifrada_e_auditada(self):
        rid = self.arquivo()
        leitura = self.client(2).get(f'/estudos/conteudos/{rid}/arquivo?modo=ler')
        self.assertEqual(leitura.status_code, 200)
        self.assertTrue(leitura.data.startswith(b'%PDF'))
        self.assertIn('attachment', leitura.headers['Content-Disposition'])  # endereço direto continua baixando
        self.assertEqual(leitura.headers['Cache-Control'], 'no-store')
        self.assertEqual(leitura.headers['X-Content-Type-Options'], 'nosniff')
        self.client(2).get(f'/estudos/conteudos/{rid}/arquivo')
        self.assertEqual(self.acoes(rid), ['ler_arquivo', 'baixar_arquivo'])
        self.assertEqual(self.client(5).get(f'/estudos/conteudos/{rid}/arquivo?modo=ler').status_code, 404)
        for arquivo in Path(self.fixture.folder.name).rglob('*.enc'):
            self.assertNotIn(b'%PDF', arquivo.read_bytes())

    def test_politica_de_seguranca_nao_ganha_excecao(self):
        rid = self.arquivo()
        csp = self.client(2).get(f'/estudos/conteudos/{rid}').headers['Content-Security-Policy']
        self.assertIn('frame-src https://www.youtube-nocookie.com;', csp + ';')
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)

    def test_video_do_youtube_embutido_sob_clique(self):
        rid = self.material(tipo='link', titulo='Vídeo', link='https://www.youtube.com/watch?v=aqz-KE-bpKQ')
        html = self.client(2).get(f'/estudos/conteudos/{rid}').get_data(as_text=True)
        self.assertIn('data-video="aqz-KE-bpKQ"', html)
        self.assertIn('Assistir ao vídeo aqui', html)
        self.assertNotIn('<iframe', html)  # só carrega depois do clique

    def test_outro_link_continua_saindo_em_nova_aba(self):
        rid = self.material(tipo='link', titulo='Site', link='https://exemplo.test/aula')
        html = self.client(2).get(f'/estudos/conteudos/{rid}').get_data(as_text=True)
        self.assertNotIn('data-video', html)
        self.assertIn('target="_blank" rel="noopener noreferrer"', html)
        self.assertIn('abre em uma nova aba', html)

    def test_visto_registrado_uma_vez_e_mostrado_na_lista(self):
        rid = self.material(tipo='link', titulo='Site', link='https://exemplo.test/aula')
        outro = self.material(tipo='link', titulo='Outro', link='https://exemplo.test/outro')
        lista = self.client(2).get('/estudos/disciplinas/1?aba=materiais').get_data(as_text=True)
        self.assertIn('0 de 2 vistos', lista)
        self.assertIn('Marcado como visto', self.client(2).get(f'/estudos/conteudos/{rid}').get_data(as_text=True))
        self.assertIn('Você já estudou este material', self.client(2).get(f'/estudos/conteudos/{rid}').get_data(as_text=True))
        self.assertEqual(self.acoes(rid), ['visualizar'])
        lista = self.client(2).get('/estudos/disciplinas/1?aba=materiais').get_data(as_text=True)
        self.assertIn('1 de 2 vistos', lista)
        self.assertIn('✓ Visto', lista)
        self.assertIn('Novo', lista)
        self.assertEqual(self.acoes(outro), [])

    def test_professor_nao_marca_visto(self):
        rid = self.material(tipo='link', titulo='Site', link='https://exemplo.test/aula')
        self.assertNotIn('Marcado como visto', self.client(3).get(f'/estudos/conteudos/{rid}').get_data(as_text=True))
        self.assertNotIn('visualizar', self.acoes(rid, uid=3))

    def test_anterior_e_proximo_seguem_a_lista_do_aluno(self):
        primeiro = self.material(tipo='link', titulo='Primeiro', link='https://exemplo.test/1')
        rascunho = self.create(tipo='link', titulo='Rascunho', link='https://exemplo.test/r').json['id']
        terceiro = self.material(tipo='link', titulo='Terceiro', link='https://exemplo.test/3')
        html = self.client(2).get(f'/estudos/conteudos/{terceiro}').get_data(as_text=True)
        self.assertIn('1 de 2', html)  # o rascunho não conta para o aluno
        self.assertIn(f'href="/estudos/conteudos/{primeiro}">Próximo material', html)
        self.assertNotIn(f'/estudos/conteudos/{rascunho}"', html)
        html = self.client(2).get(f'/estudos/conteudos/{primeiro}').get_data(as_text=True)
        self.assertIn(f'href="/estudos/conteudos/{terceiro}">‹ Material anterior', html)
        self.assertIn('2 de 2', html)


class LeitorCursoTests(TestCase):
    setUpClass = classmethod(lambda cls: study.StudyTests.setUpClass.__func__(cls))
    locals().update(emprestar(ms04.CourseApiTests, 'setUp', 'client', 'post', 'decide', 'create', 'version', 'edit', 'tree', 'publish', 'upload'))

    def test_recursos_da_aula_abrem_no_leitor(self):
        cid, module, chapter, lessons = self.tree(count=1)
        rid = self.upload(cid, lessons[0]).json['recurso']['id']
        link = self.client().post(f'/api/cursos/{cid}/aulas/{lessons[0]}/recursos', json={'tipo': 'link', 'titulo': 'Vídeo extra',
            'link': 'https://youtu.be/aqz-KE-bpKQ', 'versao': self.version(cid)},
            headers={'X-CSRF-Token': 'study-csrf', 'Idempotency-Key': uuid4().hex})
        self.assertEqual(link.status_code, 201, link.text)
        offer = self.publish(cid)
        self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{lessons[0]}/abrir', {'versao': 0}, uid=2).status_code, 200)
        html = self.client(2).get(f'/aprendizagem/ofertas/{offer}?aula={lessons[0]}').get_data(as_text=True)
        leitura = f'/api/aprender/{offer}/aulas/{lessons[0]}/recursos/{rid}/arquivo?modo=ler'
        self.assertIn(f'data-src="{leitura}"', html)
        self.assertIn('data-video="aqz-KE-bpKQ"', html)
        self.assertIn('js/paginas/leitor_material.js', html)
        self.assertNotIn('cursos_ms04.js', html)
        self.assertEqual(self.client(2).get(leitura).status_code, 200)
        with get_session() as db:
            self.assertEqual(db.query(AuditoriaCursoModel).filter_by(acao='ms04_ler_recurso').count(), 1)


class LeitorArquivosTests(TestCase):
    def test_pdfjs_local_com_licenca_e_sem_recurso_externo(self):
        for nome in ('pdf.min.mjs', 'pdf.worker.min.mjs', 'LICENSE'):
            self.assertTrue((VENDOR / nome).is_file(), nome)
        script = (APP / 'static/js/paginas/leitor_material.js').read_text(encoding='utf-8')
        self.assertIn('isEvalSupported: false', script)
        self.assertIn('disableRange: true', script)
        self.assertNotIn('https://', script.replace('https://www.youtube-nocookie.com/embed/', ''))
