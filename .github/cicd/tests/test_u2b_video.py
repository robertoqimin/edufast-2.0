"""U2b (plano de UX, O7): o professor envia vídeo (MP4/WebM até 300 MiB) em partes; o vídeo fica
cifrado em blocos e o aluno assiste por partes (Range), sem baixar o arquivo inteiro."""
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

import test_cursos_ms04 as ms04
import test_estudos as study
from app.concurrency import MutationConflict
from app.database import get_session
from app.models import AuditoriaEstudoModel, ConteudoEstudoModel
from app.services import video_envio

MIB = 1024 * 1024
MARCA = b'MARCA-EM-CLARO-DO-VIDEO-U2B-0123456789'


def video(tamanho=9 * MIB + MIB // 2):
    """MP4 fictício: cabeçalho 'ftyp' e conteúdo com uma marca que não pode aparecer no disco."""
    corpo = (MARCA + bytes(range(256))) * (tamanho // (len(MARCA) + 256) + 1)
    return (b'\x00\x00\x00\x18ftypmp42' + corpo)[:tamanho]


def emprestar(origem, *nomes):
    return {n: getattr(origem, n) for n in nomes}


class Base(TestCase):
    setUpClass = classmethod(lambda cls: study.StudyTests.setUpClass.__func__(cls))
    locals().update(emprestar(study.StudyTests, 'setUp', 'client', 'post', 'create', 'propose', 'decide', 'publish'))

    H = {'X-CSRF-Token': 'study-csrf'}

    def iniciar(self, tamanho, uid=3):
        return self.client(uid).post('/videos/envios', json={'tamanho': tamanho}, headers=self.H)

    def parte(self, token, inicio, dados, uid=3):
        return self.client(uid).put(f'/videos/envios/{token}/partes?inicio={inicio}', data=dados,
                                    headers={**self.H, 'Content-Type': 'application/octet-stream'})

    def enviar(self, dados, uid=3):
        r = self.iniciar(len(dados), uid)
        self.assertEqual(r.status_code, 201, r.text)
        token = r.json['id']
        for inicio in range(0, len(dados), video_envio.PARTE):
            r = self.parte(token, inicio, dados[inicio:inicio + video_envio.PARTE], uid)
            self.assertEqual(r.status_code, 200, r.text)
        return token

    def material(self, token, **extra):
        return self.post('/estudos/disciplinas/1/novo?formato=json',
                         {'tipo': 'arquivo', 'titulo': 'Aula em vídeo', 'texto': '', 'envio_video': token, **extra})

    def pasta(self, nome):
        return Path(self.fixture.folder.name).rglob(f'{nome}/*')


class EnvioTests(Base):
    def test_envio_em_partes_retoma_e_cria_material_cifrado(self):
        dados = video()
        token = self.iniciar(len(dados)).json['id']
        primeira = dados[:video_envio.PARTE]
        self.assertEqual(self.parte(token, 0, primeira).json['recebido'], video_envio.PARTE)
        self.assertEqual(self.parte(token, 0, primeira).json['recebido'], video_envio.PARTE)   # reenvio (retomada)
        self.assertEqual(self.parte(token, MIB, dados[MIB:2 * MIB]).json['recebido'], video_envio.PARTE)  # trecho já recebido
        salto = video_envio.PARTE + MIB
        self.assertEqual(self.parte(token, salto, dados[salto:salto + MIB]).status_code, 409)    # à frente: fora de ordem
        self.assertEqual(self.parte(token, video_envio.PARTE, dados[video_envio.PARTE:]).json['recebido'], len(dados))
        r = self.material(token)
        self.assertEqual(r.status_code, 201, r.text)
        with get_session() as db:
            row = db.get(ConteudoEstudoModel, r.json['id'])
            self.assertEqual((row.tipo, row.mime, row.tamanho, row.estado), ('arquivo', 'video/mp4', len(dados), 'rascunho'))
        cifrado = (Path(self.fixture.folder.name).rglob(row.arquivo).__next__()).read_bytes()
        self.assertNotIn(MARCA, cifrado)
        self.assertNotIn(b'ftypmp42', cifrado)
        self.assertEqual(len(cifrado), video_envio.tamanho_cifrado(len(dados)))
        self.assertEqual(list(self.pasta('videos_envio')), [])                                 # envio apagado
        self.assertEqual(self.material(token).status_code, 404)                                  # envio não é reutilizável

    def test_formato_tamanho_dono_e_limites(self):
        self.assertEqual(self.iniciar(300 * MIB + 1).status_code, 400)
        token = self.iniciar(2 * MIB).json['id']
        self.assertEqual(self.parte(token, 0, b'%PDF-1.4' + bytes(2 * MIB - 8)).status_code, 400)
        self.assertEqual(self.client(3).get(f'/videos/envios/{token}').status_code, 404)         # envio descartado
        token = self.iniciar(2 * MIB).json['id']
        self.assertEqual(self.parte(token, 0, video(MIB + 10)).status_code, 400)                 # parte intermediária fora do bloco
        self.assertIn(self.client(4).get(f'/videos/envios/{token}').status_code, (403, 404))    # outra pessoa
        self.assertEqual(self.iniciar(MIB, uid=2).status_code, 403)                              # aluno não envia
        self.assertEqual(self.iniciar(MIB).status_code, 201)
        self.assertEqual(self.iniciar(MIB).status_code, 201)
        self.assertEqual(self.iniciar(MIB).status_code, 429)                                     # 3 envios em andamento
        self.assertEqual(self.material(token).status_code, 409)                                  # envio incompleto

    def test_material_recusado_devolve_o_video_ao_envio(self):
        dados = video(3 * MIB)
        token = self.enviar(dados)
        self.assertGreaterEqual(self.material(token, secao_id='999').status_code, 400)
        estado = self.client(3).get(f'/videos/envios/{token}').json
        self.assertEqual(estado['recebido'], len(dados))
        self.assertEqual(self.material(token).status_code, 201)

    def test_webm_aceito(self):
        dados = (b'\x1a\x45\xdf\xa3' + bytes(range(256)) * 9000)[:2 * MIB + 7]
        r = self.material(self.enviar(dados))
        self.assertEqual(r.status_code, 201, r.text)
        with get_session() as db:
            self.assertEqual(db.get(ConteudoEstudoModel, r.json['id']).mime, 'video/webm')


class AssistirTests(Base):
    def publicado(self, dados):
        rid = self.material(self.enviar(dados)).json['id']
        self.publish(rid)
        return rid

    def test_aluno_assiste_por_partes_e_auditoria_conta_uma_leitura(self):
        dados = video()
        rid = self.publicado(dados)
        url = f'/estudos/conteudos/{rid}/arquivo'
        r = self.client(2).get(url + '?modo=ler', headers={'Range': 'bytes=0-'})
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.headers['Content-Range'], f'bytes 0-{video_envio.RESPOSTA - 1}/{len(dados)}')
        self.assertEqual(r.data, dados[:video_envio.RESPOSTA])
        self.assertEqual(r.headers['Accept-Ranges'], 'bytes')
        self.assertEqual(r.headers['Cache-Control'], 'no-store')
        r = self.client(2).get(url + '?modo=ler', headers={'Range': 'bytes=9000000-9000099'})
        self.assertEqual((r.status_code, r.data), (206, dados[9000000:9000100]))
        r = self.client(2).get(url + '?modo=ler', headers={'Range': f'bytes=-{MIB + 5}'})
        self.assertEqual(r.data, dados[-(MIB + 5):])
        self.assertEqual(self.client(2).get(url, headers={'Range': f'bytes={len(dados)}-'}).status_code, 416)
        inteiro = self.client(2).get(url)
        self.assertEqual((inteiro.status_code, inteiro.data), (200, dados))
        self.assertIn('attachment', inteiro.headers['Content-Disposition'])
        with get_session() as db:
            acoes = [a for a, in db.query(AuditoriaEstudoModel.acao).filter_by(conteudo_id=rid, ator_id=2)]
        self.assertEqual(acoes, ['ler_arquivo', 'baixar_arquivo'])
        self.assertEqual(self.client(5).get(url, headers={'Range': 'bytes=0-'}).status_code, 404)

    def test_pagina_mostra_o_player_sem_o_leitor_de_pdf(self):
        rid = self.publicado(video(2 * MIB))
        html = self.client(2).get(f'/estudos/conteudos/{rid}').get_data(as_text=True)
        self.assertIn(f'<video controls playsinline preload="metadata" src="/estudos/conteudos/{rid}/arquivo?modo=ler"', html)
        self.assertNotIn('leitor_material.js', html)
        self.assertIn('Baixar uma cópia', html)
        lista = self.client(2).get('/estudos/disciplinas/1?aba=materiais').get_data(as_text=True)
        self.assertIn('Vídeo', lista)

    def test_adulteracao_e_corte_sao_detectados(self):
        dados = video(3 * MIB)
        rid = self.publicado(dados)
        with get_session() as db:
            nome = db.get(ConteudoEstudoModel, rid).arquivo
        caminho = next(Path(self.fixture.folder.name).rglob(nome))
        original = caminho.read_bytes()
        alterado = bytearray(original)
        alterado[video_envio.CABECALHO + MIB + 100] ^= 1                  # um bit no 2º bloco
        caminho.write_bytes(bytes(alterado))
        list(video_envio.ler(caminho, len(dados), 0, MIB - 1))           # 1º bloco segue íntegro
        with self.assertRaises(MutationConflict):
            list(video_envio.ler(caminho, len(dados), MIB, 2 * MIB - 1))
        caminho.write_bytes(original[:-1])                                # corte
        with self.assertRaises(MutationConflict):
            list(video_envio.ler(caminho, len(dados), 0, 10))
        self.assertEqual(self.client(2).get(f'/estudos/conteudos/{rid}/arquivo', headers={'Range': 'bytes=0-'}).status_code, 409)

    def test_formulario_oferece_video_sem_travar_quem_nao_tem_javascript(self):
        html = self.client(3).get('/estudos/disciplinas/1/novo').get_data(as_text=True)
        self.assertIn('data-envio-video="/videos/envios"', html)
        self.assertIn('<fieldset class="campo-video" data-study-field="video" hidden disabled>', html)
        self.assertIn('js/paginas/envio_video.js', html)


class CursoVideoTests(TestCase):
    setUpClass = classmethod(lambda cls: study.StudyTests.setUpClass.__func__(cls))
    locals().update(emprestar(ms04.CourseApiTests, 'setUp', 'client', 'post', 'decide', 'create', 'version', 'edit', 'tree', 'publish'))
    iniciar, parte, enviar, H = Base.iniciar, Base.parte, Base.enviar, Base.H

    def test_video_da_aula_aparece_no_topo_e_toca_por_partes(self):
        cid, module, chapter, lessons = self.tree(count=1)
        dados = video(2 * MIB + 3)
        r = self.client().post(f'/api/cursos/{cid}/aulas/{lessons[0]}/recursos', json={'tipo': 'arquivo', 'titulo': 'Vídeo da aula',
            'versao': self.version(cid), 'envio_video': self.enviar(dados)}, headers={**self.H, 'Idempotency-Key': uuid4().hex})
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json['recurso']['id']
        self.assertEqual(r.json['recurso']['mime'], 'video/mp4')
        editor = self.client().get(f'/aprendizagem/cursos/{cid}/aulas/{lessons[0]}').get_data(as_text=True)
        self.assertIn('<video controls', editor)
        self.assertIn('Enviar vídeo', editor)
        offer = self.publish(cid)
        self.assertEqual(self.post(f'/api/aprender/{offer}/aulas/{lessons[0]}/abrir', {'versao': 0}, uid=2).status_code, 200)
        html = self.client(2).get(f'/aprendizagem/ofertas/{offer}?aula={lessons[0]}').get_data(as_text=True)
        src = f'/api/aprender/{offer}/aulas/{lessons[0]}/recursos/{rid}/arquivo?modo=ler'
        self.assertIn(f'src="{src}"', html)
        self.assertNotIn('Para praticar', html)          # o único vídeo já está no topo da aula
        parte = self.client(2).get(src, headers={'Range': 'bytes=0-'})
        self.assertEqual((parte.status_code, parte.data), (206, dados))


class RegraDoBancoTests(TestCase):
    setUpClass = classmethod(lambda cls: study.StudyTests.setUpClass.__func__(cls))
    setUp = study.StudyTests.setUp

    def inserir(self, mime, tamanho):
        with get_session() as db:
            db.add(ConteudoEstudoModel(turma_disciplina_id=1, autor_id=3, tipo='arquivo', titulo='x', texto='', link='',
                                       arquivo=uuid4().hex + '.enc', mime=mime, tamanho=tamanho))
            db.commit()

    def test_009_video_ate_300_mib_e_pdf_continua_ate_5_mib(self):
        self.inserir('video/mp4', 300 * MIB)
        for mime, tamanho in (('video/webm', 300 * MIB + 1), ('application/pdf', 5 * MIB + 1)):
            with self.subTest(mime=mime), self.assertRaises(IntegrityError):
                self.inserir(mime, tamanho)
