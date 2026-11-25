"""U2b: envio de vídeo em partes (professor e administração). O material em si é criado depois,
pelo formulário normal do Espaço da disciplina ou do recurso de aula, citando o envio."""
from flask import Blueprint, current_app, g, jsonify, request

from app.concurrency import MutationConflict
from app.services import video_envio
from app.services.identidade_service import require_role
from config import caminho_uploads

video_bp = Blueprint('videos', __name__)


def uploads():
    return caminho_uploads(current_app.config['UPLOAD_FOLDER'])


@video_bp.before_request
def somente_docentes():
    g.video_identity = require_role('professor', 'admin', 'super_admin')


@video_bp.after_request
def sem_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@video_bp.post('/videos/envios')
def iniciar():
    dados = request.get_json(silent=True) or {}
    return jsonify(video_envio.iniciar(uploads(), g.video_identity.id, dados.get('tamanho'))), 201


@video_bp.put('/videos/envios/<token>/partes')
def parte(token):
    if request.content_length is None:
        raise MutationConflict('Parte do vídeo sem tamanho.', 411)
    if request.content_length > video_envio.PARTE:
        raise MutationConflict('Parte do vídeo grande demais.', 413)
    corpo = request.get_data(cache=False)
    return jsonify(video_envio.receber(uploads(), token, g.video_identity.id, request.args.get('inicio'), corpo))


@video_bp.get('/videos/envios/<token>')
def estado(token):
    return jsonify(video_envio.estado(uploads(), token, g.video_identity.id))
