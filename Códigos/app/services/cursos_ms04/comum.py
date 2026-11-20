"""Autorização e transação compartilhadas pelo backend MS04."""
from sqlalchemy import inspect
from app.concurrency import MutationConflict, check_version, insert_if_missing
from app.models import UsuarioModel, CursoVersaoModel, AulaModel, TemaModel, CapituloModel
from app.services import cursos as base

TABLES = {'curso_versoes','curso_aula_conteudos','curso_retomadas','curso_aula_recursos'}


def habilitado(db, *, required=True):
    schema = inspect(db.connection())
    present = TABLES & set(schema.get_table_names())
    ready = present == TABLES and next(c for c in schema.get_columns('curso_aulas') if c['name']=='video_id')['nullable']
    if required and not ready:
        raise MutationConflict('A API de cursos aguarda habilitação revisada nesta instalação.',503)
    return ready


def inteiro(value, *, zero=False):
    text = str(value)
    if isinstance(value,bool) or not text.isascii() or not text.isdigit() or len(text)>10:
        raise MutationConflict('Identificador ou versão inválido.',400)
    result = int(text)
    if not (0 if zero else 1) <= result <= 2147483647:
        raise MutationConflict('Identificador ou versão inválido.',400)
    return result


def usuario(db, ator_id, roles=('admin','super_admin','professor')):
    row = db.get(UsuarioModel,inteiro(ator_id))
    if not row or row.estado != 'ativo' or row.tipo not in roles:
        raise MutationConflict('Acesso não autorizado ou revogado.',403)
    return row


def autoria(db, ator_id, curso_id, *, editar=False):
    user = usuario(db,ator_id)
    return base.autoria(db,inteiro(curso_id),user.id,user.tipo,editar=editar)


def revisao(db, curso_id):
    return insert_if_missing(db,CursoVersaoModel,curso_id=curso_id,defaults={'versao':1})


def versao(db, curso_id):
    row = db.query(CursoVersaoModel).filter_by(curso_id=curso_id).first()
    return row.versao if row else 1


def exigir_versao(row, payload, *, incrementar=True):
    if 'versao' not in payload:
        raise MutationConflict('Informe a versão atual antes de salvar.',428)
    expected = inteiro(payload['versao'],zero=True)
    if incrementar:
        check_version(row,{'versao':expected})
    elif row.versao != expected:
        raise MutationConflict('Registro alterado por outro envio; recarregue antes de salvar.')


def aula(db, curso_id, aula_id):
    row = db.query(AulaModel).join(TemaModel).join(CapituloModel).filter(
        AulaModel.id==inteiro(aula_id),CapituloModel.curso_id==curso_id).first()
    if not row:
        raise MutationConflict('Aula não encontrada nesta oferta.',404)
    return row


def campos(payload, permitidos):
    if set(payload)-set(permitidos)-{'csrf_token','idempotency_key'}:
        raise MutationConflict('Campos não permitidos nesta operação.',400)
