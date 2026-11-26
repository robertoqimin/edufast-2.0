"""U2b: vídeos enviados pelo professor (MP4/WebM, até 300 MiB), cifrados em blocos.

Formato do arquivo cifrado (``<hex>.enc``, mesmas pastas dos demais materiais):

    MAGIA (14 B) | tamanho do bloco (u32) | tamanho total (u64) | prefixo do nonce (8 B)
    bloco 0 cifrado | bloco 1 cifrado | ...       (cada bloco: até 1 MiB + 16 B de etiqueta)

- AES-256-GCM com chave derivada da DATA_ENCRYPTION_KEY por HKDF (rótulo próprio de vídeo).
- Nonce = prefixo aleatório do arquivo + número do bloco: nunca se repete no mesmo arquivo.
- Dados autenticados = cabeçalho + número do bloco + "é o último": trocar, reordenar, cortar
  ou estender blocos é detectado; o tamanho total também é autenticado.
- Assistir e avançar: só os blocos pedidos (``Range``) são decifrados; cada resposta parcial
  entrega no máximo RESPOSTA bytes, para não prender uma thread do servidor pelo vídeo inteiro.

Envio em partes (o servidor recebe no máximo 16 MB por requisição): o navegador abre um envio,
manda partes de 8 MiB em ordem e, ao fim, o formulário normal (material ou recurso de aula)
cita o envio. Cada parte já é cifrada ao chegar; nada fica em claro no disco. Envios
abandonados são apagados em 24 h. Reenviar uma parte já recebida é aceito sem efeito (retomada).
"""
import json
import os
import re
import secrets
import shutil
import struct
import time
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from flask import Response, request

from app.concurrency import MutationConflict

BLOCO = 1024 * 1024
PARTE = 8 * BLOCO
LIMITE = 300 * 1024 * 1024          # 314572800, o mesmo da regra 009 no banco
RESPOSTA = 4 * BLOCO
MIMES = {'video/mp4': '.mp4', 'video/webm': '.webm'}
MAGIA = b'EDUFAST-VID-1\n'
CABECALHO = len(MAGIA) + 4 + 8 + 8
VALIDADE = 24 * 3600
MAX_ENVIOS = 3
FOLGA_DISCO = 512 * 1024 * 1024
_TOKEN = re.compile(r'^[0-9a-f]{32}$')


def eh_video(mime):
    return mime in MIMES


def _chave():
    import base64
    from config import Config
    bruta = base64.urlsafe_b64decode(Config.DATA_ENCRYPTION_KEY.encode('ascii'))
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b'edufast-video',
                info=b'aes-256-gcm-blocos-v1').derive(bruta)


def _cabecalho(total, prefixo):
    return MAGIA + struct.pack('>IQ', BLOCO, total) + prefixo


def _aad(cabecalho, indice, ultimo):
    return cabecalho + struct.pack('>I?', indice, ultimo)


def _blocos(total):
    return (total + BLOCO - 1) // BLOCO


def tamanho_cifrado(total):
    return CABECALHO + total + 16 * _blocos(total)


def detectar_mime(inicio):
    if len(inicio) >= 12 and inicio[4:8] == b'ftyp':
        return 'video/mp4'
    if inicio.startswith(b'\x1a\x45\xdf\xa3'):
        return 'video/webm'
    return None


# ---------- envio em partes ----------

def _pasta_envios(uploads):
    pasta = Path(uploads) / 'videos_envio'
    pasta.mkdir(parents=True, exist_ok=True, mode=0o700)
    return pasta


def _sessao(uploads, token, usuario_id):
    if not isinstance(token, str) or not _TOKEN.match(token):
        raise MutationConflict('Envio de vídeo não encontrado. Envie o vídeo de novo.', 404)
    pasta = _pasta_envios(uploads) / token
    try:
        meta = json.loads((pasta / 'meta.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise MutationConflict('Envio de vídeo não encontrado. Envie o vídeo de novo.', 404)
    if meta.get('usuario') != usuario_id or time.time() - meta.get('criado', 0) > VALIDADE:
        raise MutationConflict('Envio de vídeo não encontrado. Envie o vídeo de novo.', 404)
    return pasta, meta


def _gravar_meta(pasta, meta):
    temporario = pasta / 'meta.json.tmp'
    temporario.write_text(json.dumps(meta), encoding='utf-8')
    os.replace(temporario, pasta / 'meta.json')


def limpar(uploads, agora=None):
    """Apaga envios abandonados (mais de 24 h)."""
    agora = agora or time.time()
    for pasta in _pasta_envios(uploads).iterdir():
        try:
            criado = json.loads((pasta / 'meta.json').read_text(encoding='utf-8')).get('criado', 0)
        except (OSError, ValueError):
            criado = pasta.stat().st_mtime
        if agora - criado > VALIDADE:
            shutil.rmtree(pasta, ignore_errors=True)


def iniciar(uploads, usuario_id, tamanho):
    try:
        tamanho = int(tamanho)
    except (TypeError, ValueError):
        raise MutationConflict('Informe o tamanho do vídeo.', 400)
    if not 1 <= tamanho <= LIMITE:
        raise MutationConflict('O vídeo pode ter até 300 MB. Reduza a resolução ou divida em partes.', 400)
    limpar(uploads)
    base = _pasta_envios(uploads)
    ativos = 0
    for pasta in base.iterdir():
        try:
            ativos += json.loads((pasta / 'meta.json').read_text(encoding='utf-8')).get('usuario') == usuario_id
        except (OSError, ValueError):
            continue
    if ativos >= MAX_ENVIOS:
        raise MutationConflict('Você já tem 3 envios de vídeo em andamento. Conclua um deles ou aguarde 24 h.', 429)
    if shutil.disk_usage(base).free < tamanho_cifrado(tamanho) + FOLGA_DISCO:
        raise MutationConflict('Sem espaço no servidor para este vídeo. Avise a administração.', 507)
    token = secrets.token_hex(16)
    pasta = base / token
    pasta.mkdir(mode=0o700)
    with (pasta / 'dados.part').open('xb') as arquivo:
        arquivo.write(_cabecalho(tamanho, secrets.token_bytes(8)))
    _gravar_meta(pasta, {'usuario': usuario_id, 'tamanho': tamanho, 'recebido': 0, 'mime': None, 'criado': time.time()})
    return {'id': token, 'tamanho': tamanho, 'recebido': 0, 'parte': PARTE}


class _Trava:
    """Uma parte por vez em cada envio, também entre processos (arquivo exclusivo)."""
    def __init__(self, pasta):
        self.caminho = pasta / 'trava'

    def __enter__(self):
        try:
            fd = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if time.time() - self.caminho.stat().st_mtime < 120:
                raise MutationConflict('Outra parte deste vídeo está sendo gravada. Tente de novo.', 409)
            self.caminho.unlink(missing_ok=True)
            fd = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        return self

    def __exit__(self, *erro):
        self.caminho.unlink(missing_ok=True)


def receber(uploads, token, usuario_id, inicio, dados):
    pasta, meta = _sessao(uploads, token, usuario_id)
    try:
        inicio = int(inicio)
    except (TypeError, ValueError):
        raise MutationConflict('Parte do vídeo sem posição.', 400)
    with _Trava(pasta):
        pasta, meta = _sessao(uploads, token, usuario_id)
        recebido, tamanho = meta['recebido'], meta['tamanho']
        if inicio < recebido and inicio + len(dados) <= recebido:
            return {'id': token, 'recebido': recebido, 'tamanho': tamanho}   # parte repetida (retomada)
        if inicio != recebido:
            raise MutationConflict(f'Parte fora de ordem: o servidor espera a posição {recebido}.', 409)
        final = recebido + len(dados) == tamanho
        if not dados or len(dados) > PARTE or recebido + len(dados) > tamanho or (not final and len(dados) % BLOCO):
            raise MutationConflict('Parte do vídeo com tamanho inválido.', 400)
        if recebido == 0:
            meta['mime'] = detectar_mime(dados[:16])
            if not meta['mime']:
                shutil.rmtree(pasta, ignore_errors=True)
                raise MutationConflict('Formato não aceito. Envie vídeo MP4 ou WebM.', 400)
        caminho = pasta / 'dados.part'
        with caminho.open('r+b') as arquivo:
            cabecalho = arquivo.read(CABECALHO)
            prefixo = cabecalho[-8:]
            esperado = CABECALHO + recebido + 16 * (recebido // BLOCO)
            arquivo.truncate(esperado)       # descarta resto de uma gravação interrompida
            arquivo.seek(esperado)
            aes = AESGCM(_chave())
            for deslocamento in range(0, len(dados), BLOCO):
                pedaco = dados[deslocamento:deslocamento + BLOCO]
                indice = (recebido + deslocamento) // BLOCO
                ultimo = recebido + deslocamento + len(pedaco) == tamanho
                arquivo.write(aes.encrypt(prefixo + struct.pack('>I', indice), pedaco, _aad(cabecalho, indice, ultimo)))
            arquivo.flush()
            os.fsync(arquivo.fileno())
        meta['recebido'] = recebido + len(dados)
        _gravar_meta(pasta, meta)
        return {'id': token, 'recebido': meta['recebido'], 'tamanho': tamanho, 'mime': meta['mime']}


def estado(uploads, token, usuario_id):
    _, meta = _sessao(uploads, token, usuario_id)
    return {'id': token, 'recebido': meta['recebido'], 'tamanho': meta['tamanho'], 'mime': meta['mime']}


def consumir(uploads, token, usuario_id, destino):
    """Move o vídeo completo para a pasta final; devolve (caminho, metadados para o banco)."""
    pasta, meta = _sessao(uploads, token, usuario_id)
    if meta['recebido'] != meta['tamanho'] or not meta['mime']:
        raise MutationConflict('O envio do vídeo ainda não terminou.', 409)
    origem = pasta / 'dados.part'
    if origem.stat().st_size != tamanho_cifrado(meta['tamanho']):
        raise MutationConflict('Envio de vídeo incompleto. Envie o vídeo de novo.', 409)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True, mode=0o700)
    alvo = destino / (secrets.token_hex(16) + '.enc')
    os.replace(origem, alvo)
    alvo.chmod(0o600)
    (pasta / 'usado.json').write_text(json.dumps({'arquivo': str(alvo)}), encoding='utf-8')
    return alvo, {'arquivo': alvo.name, 'mime': meta['mime'], 'tamanho': meta['tamanho']}


def finalizar(uploads, token, usuario_id):
    """Depois de gravar no banco: apaga a pasta do envio."""
    try:
        pasta, _ = _sessao(uploads, token, usuario_id)
    except MutationConflict:
        return
    shutil.rmtree(pasta, ignore_errors=True)


def devolver(uploads, token, usuario_id, alvo):
    """Se o banco recusou o material, o vídeo volta para o envio (o professor não reenvia 300 MB)."""
    try:
        pasta, _ = _sessao(uploads, token, usuario_id)
        os.replace(alvo, pasta / 'dados.part')
        (pasta / 'usado.json').unlink(missing_ok=True)
    except (MutationConflict, OSError):
        Path(alvo).unlink(missing_ok=True)


# ---------- leitura e resposta ----------

def _abrir(caminho, tamanho):
    with open(caminho, 'rb') as arquivo:
        cabecalho = arquivo.read(CABECALHO)
    if len(cabecalho) != CABECALHO or not cabecalho.startswith(MAGIA):
        raise MutationConflict('Vídeo indisponível. Avise a administração.', 409)
    bloco, total = struct.unpack('>IQ', cabecalho[len(MAGIA):len(MAGIA) + 12])
    if bloco != BLOCO or total != tamanho or os.path.getsize(caminho) != tamanho_cifrado(total):
        raise MutationConflict('Vídeo indisponível. Avise a administração.', 409)
    return cabecalho


def ler(caminho, tamanho, inicio, fim):
    """Bytes decifrados de [inicio, fim] (inclusive), bloco a bloco."""
    cabecalho = _abrir(caminho, tamanho)
    prefixo = cabecalho[-8:]
    aes = AESGCM(_chave())
    with open(caminho, 'rb') as arquivo:
        for indice in range(inicio // BLOCO, fim // BLOCO + 1):
            claro_ini = indice * BLOCO
            n = min(BLOCO, tamanho - claro_ini)
            arquivo.seek(CABECALHO + claro_ini + 16 * indice)
            cifrado = arquivo.read(n + 16)
            try:
                claro = aes.decrypt(prefixo + struct.pack('>I', indice), cifrado,
                                    _aad(cabecalho, indice, claro_ini + n == tamanho))
            except InvalidTag:
                raise MutationConflict('Vídeo indisponível. Avise a administração.', 409)
            yield claro[max(inicio, claro_ini) - claro_ini:min(fim, claro_ini + n - 1) - claro_ini + 1]


def intervalo(tamanho):
    """(inicio, fim, parcial) a partir do cabeçalho Range; None se o intervalo é inválido."""
    pedido = request.headers.get('Range')
    if not pedido:
        return 0, tamanho - 1, False
    achado = re.fullmatch(r'bytes=(\d*)-(\d*)', pedido.strip())
    if not achado or achado.groups() == ('', ''):
        return None
    a, b = achado.groups()
    if a == '':
        inicio, fim = max(0, tamanho - int(b)), tamanho - 1
    else:
        inicio, fim = int(a), min(int(b) if b else tamanho - 1, tamanho - 1)
    if inicio > fim or inicio >= tamanho:
        return None
    return inicio, min(fim, inicio + RESPOSTA - 1), True


def responder(caminho, mime, tamanho, nome_download):
    faixa = intervalo(tamanho)
    if faixa is None:
        resposta = Response(status=416)
        resposta.headers['Content-Range'] = f'bytes */{tamanho}'
        return resposta
    inicio, fim, parcial = faixa
    _abrir(caminho, tamanho)  # erro de arquivo vira 409 antes de começar a enviar
    resposta = Response(ler(caminho, tamanho, inicio, fim), status=206 if parcial else 200, mimetype=mime,
                        direct_passthrough=True)
    resposta.headers['Content-Length'] = str(fim - inicio + 1)
    resposta.headers['Accept-Ranges'] = 'bytes'
    if parcial:
        resposta.headers['Content-Range'] = f'bytes {inicio}-{fim}/{tamanho}'
    from urllib.parse import quote
    resposta.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(nome_download)}"
    resposta.headers['Cache-Control'] = 'no-store'
    resposta.headers['X-Content-Type-Options'] = 'nosniff'
    return resposta


def primeira_leitura():
    """Auditar só o pedido que começa o vídeo, não cada pedaço buscado pelo player."""
    faixa = request.headers.get('Range', '')
    return not faixa or re.fullmatch(r'bytes=0-\d*', faixa.strip()) is not None
