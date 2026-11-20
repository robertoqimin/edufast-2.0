"""Ponto de implementação MS04-D: aula em texto/vídeo e recursos privados.

Preservar o validador YouTube e IDs legados. Texto não usa ID fictício de vídeo.
Arquivos requerem autorização pela oferta/aula, cifra, limites e rollback de
gravação. Não reutilizar downloads de documentos pessoais ou atestados.
"""


from pathlib import Path
from uuid import uuid4
from cryptography.fernet import InvalidToken
from flask import current_app
from app.concurrency import MutationConflict
from app.models import AulaConteudoCursoModel, RecursoAulaCursoModel
from app.services import cursos as base
from app.services.estudo_service import fields
from . import comum

LIMIT = 5*1024*1024


def validar_aula(dados):
    kind = dados.get('tipo_aula','video')
    body,description = base.texto(dados.get('corpo','')),base.texto(dados.get('descricao',''))
    if kind=='video':
        video = base.video_id(dados.get('video'))
    elif kind=='texto' and body and dados.get('video') in (None,''):
        video = None
    else:
        raise MutationConflict('Escolha vídeo válido ou texto não vazio de até 10.000 caracteres.',400)
    return {'tipo':kind,'corpo':body,'video_id':video,'descricao':description}


def formato(db, row):
    content = db.get(AulaConteudoCursoModel,row.id)
    kind,body = (content.tipo,content.corpo) if content else ('video','')
    if (kind=='video' and not row.video_id) or (kind=='texto' and (row.video_id is not None or not body.strip())):
        raise MutationConflict('Conteúdo de aula inconsistente. Avise a administração.')
    return {'tipo':kind,'corpo':body}


def guardar(upload):
    from app.crypto import FILE_PREFIX,cipher
    if upload is None:
        raise MutationConflict('Anexe PDF, PNG ou JPEG de até 5 MiB.',400)
    data = upload.stream.read(LIMIT+1)
    mime = ('application/pdf' if data.startswith(b'%PDF-') else 'image/png' if data.startswith(b'\x89PNG\r\n\x1a\n')
        else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else None)
    if not mime or len(data)>LIMIT:
        raise MutationConflict('Arquivo inválido. Use PDF, PNG ou JPEG de até 5 MiB.',400)
    try:
        encoded = FILE_PREFIX+cipher().encrypt(data)
    except (ValueError,UnicodeError):
        raise MutationConflict('Envio de arquivo indisponível. Avise a administração.',503)
    folder = Path(current_app.config['UPLOAD_FOLDER'])/'materiais_curso'
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    path = folder/(uuid4().hex+'.enc')
    try:
        with path.open('xb') as file:
            file.write(encoded)
        path.chmod(0o600)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path,{'arquivo':path.name,'mime':mime,'tamanho':len(data)}


def novo_recurso(db, *, ator_id, curso_id, aula_id, payload, upload=None):
    course = comum.autoria(db,ator_id,curso_id,editar=True)
    row = comum.aula(db,course.id,aula_id)
    revision = comum.revisao(db,course.id)
    comum.exigir_versao(revision,payload)
    if db.query(RecursoAulaCursoModel).filter_by(aula_id=row.id,estado='ativo').count()>=20:
        raise MutationConflict('Cada aula admite até 20 recursos ativos.')
    kind = payload.get('tipo')
    if kind not in {'link','arquivo'}:
        raise MutationConflict('Escolha link ou arquivo.',400)
    values = fields({'tipo':kind,'titulo':payload.get('titulo'),'link':payload.get('link','')})
    values.pop('texto')
    path = None
    if kind=='arquivo':
        path,metadata = guardar(upload)
        values.update(metadata)
    elif upload:
        raise MutationConflict('Use o tipo arquivo para anexos.',400)
    try:
        resource = RecursoAulaCursoModel(aula_id=row.id,**values)
        db.add(resource)
        db.flush()
        base.auditar(db,ator_id,'ms04_criar_recurso',resource.id)
    except BaseException:
        if path:
            path.unlink(missing_ok=True)
        raise
    return resource,revision,path


def ler_arquivo(resource):
    from app.crypto import FILE_PREFIX,cipher
    name = resource.arquivo or ''
    if len(name)!=36 or not name.endswith('.enc') or any(c not in '0123456789abcdef' for c in name[:-4]):
        raise MutationConflict('Arquivo não encontrado.',404)
    path = Path(current_app.config['UPLOAD_FOLDER'])/'materiais_curso'/name
    if not path.is_file():
        raise MutationConflict('Arquivo não encontrado.',404)
    if path.stat().st_size>8*1024*1024:
        raise MutationConflict('Arquivo indisponível.')
    encoded = path.read_bytes()
    if not encoded.startswith(FILE_PREFIX):
        raise MutationConflict('Arquivo indisponível.')
    try:
        data = cipher().decrypt(encoded[len(FILE_PREFIX):])
    except (InvalidToken,ValueError,UnicodeError):
        raise MutationConflict('Arquivo indisponível. Avise a administração.')
    if len(data)!=resource.tamanho or resource.mime not in {'application/pdf','image/png','image/jpeg'}:
        raise MutationConflict('Arquivo indisponível.')
    return data
