"""Ponto de implementação MS04-B: rascunho próprio e versão do curso.

Reaproveitar cursos.autoria/estrutura/duplicar. Uma edição exige autorização,
versão do agregado, idempotência e auditoria na mesma transação. O chamador
controla commit/rollback, inclusive dentro das aprovações existentes.
"""


from app.concurrency import MutationConflict
from app.models import (CapituloModel, TemaModel, AulaModel, AulaConteudoCursoModel,
    RecursoAulaCursoModel, CursoVersaoModel, ProgressoAulaModel)
from app.services import cursos as base
from . import comum, conteudo


def salvar_rascunho(db, *, ator_id, curso_id, versao, dados, chave_envio=None):
    course = comum.autoria(db,ator_id,curso_id,editar=True)
    revision = comum.revisao(db,course.id)
    comum.exigir_versao(revision,{'versao':versao} if versao is not None else {})
    action,kind = dados.get('acao'),dados.get('tipo')
    if action=='curso':
        comum.campos(dados,{'acao','titulo','descricao','versao'})
        course.titulo,course.descricao = base.titulo(dados.get('titulo')),base.texto(dados.get('descricao',''))
        item = None
    elif kind in {'capitulo','tema','aula'} and action in {'adicionar','editar','remover','subir','descer'}:
        permitted = {'acao','tipo','versao','titulo','pai_id'} if action=='adicionar' else {'acao','tipo','versao','id'}
        if action=='editar':
            permitted.add('titulo')
        if kind=='aula' and action in {'adicionar','editar'}:
            permitted |= {'descricao','video','tipo_aula','corpo'}
        comum.campos(dados,permitted)
        model,field = {'capitulo':(CapituloModel,CapituloModel.curso_id),
            'tema':(TemaModel,TemaModel.capitulo_id),'aula':(AulaModel,AulaModel.tema_id)}[kind]
        if action=='adicionar':
            if kind=='capitulo':
                parent = course.id
            elif kind=='tema':
                chapter = base.obter(db,CapituloModel,comum.inteiro(dados.get('pai_id')))
                if chapter.curso_id!=course.id:
                    raise MutationConflict('Módulo não encontrado neste curso.',404)
                parent = chapter.id
            else:
                theme = base.obter(db,TemaModel,comum.inteiro(dados.get('pai_id')))
                if base.obter(db,CapituloModel,theme.capitulo_id).curso_id!=course.id:
                    raise MutationConflict('Capítulo não encontrado neste curso.',404)
                parent = theme.id
            values = {field.key:parent,'titulo':base.titulo(dados.get('titulo')),
                'posicao':base.proxima_posicao(db,model,field,parent)}
            spec = conteudo.validar_aula(dados) if kind=='aula' else None
            if spec:
                values.update(video_id=spec['video_id'],descricao=spec['descricao'])
            row = model(**values)
            db.add(row)
            db.flush()
            if spec:
                db.add(AulaConteudoCursoModel(aula_id=row.id,tipo=spec['tipo'],corpo=spec['corpo']))
        else:
            row = base.obter(db,model,comum.inteiro(dados.get('id')))
            if kind=='capitulo':
                owner = row.curso_id
            elif kind=='tema':
                owner = base.obter(db,CapituloModel,row.capitulo_id).curso_id
            else:
                owner = base.obter(db,CapituloModel,base.obter(db,TemaModel,row.tema_id).capitulo_id).curso_id
            if owner!=course.id:
                raise MutationConflict('Item não encontrado neste curso.',404)
            if action=='editar':
                row.titulo = base.titulo(dados.get('titulo'))
                if kind=='aula':
                    spec = conteudo.validar_aula(dados)
                    row.video_id,row.descricao = spec['video_id'],spec['descricao']
                    content = db.get(AulaConteudoCursoModel,row.id)
                    if content is None:
                        content = AulaConteudoCursoModel(aula_id=row.id,tipo=spec['tipo'],corpo=spec['corpo'])
                        db.add(content)
                    content.tipo,content.corpo = spec['tipo'],spec['corpo']
            elif action=='remover':
                if (kind=='capitulo' and db.query(TemaModel).filter_by(capitulo_id=row.id).first()
                        or kind=='tema' and db.query(AulaModel).filter_by(tema_id=row.id).first()):
                    raise MutationConflict('Remova primeiro os itens deste grupo.')
                if kind=='aula':
                    if (db.query(RecursoAulaCursoModel).filter_by(aula_id=row.id).first()
                            or db.query(ProgressoAulaModel).filter_by(aula_id=row.id).first()):
                        raise MutationConflict('Aula com recursos ou histórico é preservada. Prepare outra edição.')
                    content = db.get(AulaConteudoCursoModel,row.id)
                    if content:
                        db.delete(content)
                        db.flush()
                db.delete(row)
            else:
                candidates = db.query(model).filter(field==getattr(row,field.key))
                other = (candidates.filter(model.posicao<row.posicao).order_by(model.posicao.desc()).first()
                    if action=='subir' else candidates.filter(model.posicao>row.posicao).order_by(model.posicao).first())
                if other:
                    previous,new = row.posicao,other.posicao
                    row.posicao = -row.id
                    db.flush()
                    other.posicao = previous
                    db.flush()
                    row.posicao = new
        item = row.id
    else:
        raise MutationConflict('Operação de estrutura inválida.',400)
    base.auditar(db,ator_id,'ms04_editar_rascunho',course.id)
    db.flush()
    return {'curso_id':course.id,'versao':revision.versao,'item_id':item}


def duplicar_edicao(db, *, ator_id, curso_id, payload):
    course = comum.autoria(db,ator_id,curso_id)
    revision = comum.revisao(db,course.id)
    comum.exigir_versao(revision,payload,incrementar=False)
    new = base.duplicar(db,course,ator_id)
    db.flush()
    for previous,copied in zip(base.aulas_curso(db,course.id),base.aulas_curso(db,new.id),strict=True):
        content = db.get(AulaConteudoCursoModel,previous.id)
        if content:
            db.add(AulaConteudoCursoModel(aula_id=copied.id,tipo=content.tipo,corpo=content.corpo))
        for resource in db.query(RecursoAulaCursoModel).filter_by(aula_id=previous.id).all():
            values = {column.name:getattr(resource,column.name) for column in RecursoAulaCursoModel.__table__.columns
                if column.name not in {'id','aula_id'}}
            db.add(RecursoAulaCursoModel(aula_id=copied.id,**values))
    db.add(CursoVersaoModel(curso_id=new.id,versao=1))
    return {'curso_id':new.id,'versao':1,'origem_id':course.id}
