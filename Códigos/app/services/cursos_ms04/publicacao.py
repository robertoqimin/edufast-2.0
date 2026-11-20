"""Ponto de implementação MS04-B: solicitação da versão exata do curso.

Validar novamente autor, vínculos, versão e snapshot na decisão. Reutilizar
solicitações existentes sem ampliar o papel de revisor ou o acesso a ofertas.
Nunca aplicar publicação usando conteúdo diferente do enviado para revisão.
"""


import hashlib
import json
from app.concurrency import MutationConflict
from app.models import AulaConteudoCursoModel, RecursoAulaCursoModel, ProfessorModel
from app.services import cursos as base
from . import comum, conteudo


def snapshot(db, course):
    teacher = base.obter(db,ProfessorModel,course.professor_id)
    comum.autoria(db,teacher.usuario_id,course.id,editar=True)
    tree = base.estrutura(db,course.id)
    if not tree or any(not chapter['temas'] or any(not group['aulas'] for group in chapter['temas']) for chapter in tree):
        raise MutationConflict('Preencha os módulos, capítulos e ao menos uma aula em cada capítulo.',400)
    lessons = [a for chapter in tree for group in chapter['temas'] for a in group['aulas']]
    for lesson in lessons:
        conteudo.formato(db,lesson)
    ids = [a.id for a in lessons]
    contents = db.query(AulaConteudoCursoModel).filter(AulaConteudoCursoModel.aula_id.in_(ids)).order_by(AulaConteudoCursoModel.aula_id).all()
    resources = db.query(RecursoAulaCursoModel).filter(RecursoAulaCursoModel.aula_id.in_(ids)).order_by(RecursoAulaCursoModel.id).all()
    def values(row):
        return {column.name:getattr(row,column.name) for column in row.__table__.columns}
    data = {'curso':values(course),'estrutura':[(values(c['capitulo']),[(values(g['tema']),[values(a) for a in g['aulas']])
        for g in c['temas']]) for c in tree],'conteudos':[values(r) for r in contents],'recursos':[values(r) for r in resources]}
    return hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()


def preparar_publicacao(db, *, autor_id, curso_id, versao, aplicar=False, assinatura=None):
    comum.habilitado(db)
    comum.usuario(db,autor_id,('professor',))
    course = comum.autoria(db,autor_id,curso_id,editar=True)
    revision = comum.revisao(db,course.id)
    comum.exigir_versao(revision,{'versao':versao} if versao is not None else {},incrementar=False)
    digest = snapshot(db,course)
    if aplicar:
        if digest!=assinatura:
            raise MutationConflict('O conteúdo mudou depois do pedido. Envie a versão atual para revisão.')
        course.estado = 'publicado'
        revision.versao += 1
        base.auditar(db,autor_id,'ms04_publicar_curso',course.id)
    return {'curso_id':course.id,'versao':revision.versao if aplicar else comum.inteiro(versao),'snapshot':digest}
