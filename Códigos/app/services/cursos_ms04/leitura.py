"""Índice sem corpos de aula e biblioteca paginada por autorização SQL."""
from sqlalchemy import func
from sqlalchemy.orm import load_only
from app.models import (CursoModel, CursoVersaoModel, CapituloModel, TemaModel, AulaModel,
    AulaConteudoCursoModel, RecursoAulaCursoModel, OfertaCursoModel, ProgressoAulaModel,
    RetomadaCursoModel, TurmaDisciplinaModel, TurmaModel, AlunoModel, ProfessorDisciplinaModel)
from app.services import cursos as base
from app.services.estudo_service import pairs
from . import comum, conteudo


def indice(db, course_id):
    chapters = db.query(CapituloModel).filter_by(curso_id=course_id).order_by(CapituloModel.posicao).all()
    themes = db.query(TemaModel).join(CapituloModel).filter(CapituloModel.curso_id==course_id).order_by(TemaModel.posicao).all()
    lessons = db.query(AulaModel).options(load_only(AulaModel.id,AulaModel.tema_id,AulaModel.titulo,AulaModel.posicao)).join(
        TemaModel).join(CapituloModel).filter(CapituloModel.curso_id==course_id).order_by(
            CapituloModel.posicao,TemaModel.posicao,AulaModel.posicao).all()
    types = dict(db.query(AulaConteudoCursoModel.aula_id,AulaConteudoCursoModel.tipo).join(
        AulaModel).join(TemaModel).join(CapituloModel).filter(CapituloModel.curso_id==course_id).all())
    by_theme = {}
    for lesson in lessons:
        by_theme.setdefault(lesson.tema_id,[]).append({'id':lesson.id,'titulo':lesson.titulo,
            'posicao':lesson.posicao,'tipo':types.get(lesson.id,'video')})
    by_chapter = {}
    for theme in themes:
        by_chapter.setdefault(theme.capitulo_id,[]).append({'id':theme.id,'titulo':theme.titulo,
            'posicao':theme.posicao,'aulas':by_theme.get(theme.id,[])})
    tree = [{'id':r.id,'titulo':r.titulo,'posicao':r.posicao,'capitulos':by_chapter.get(r.id,[])} for r in chapters]
    return tree,[a['id'] for m in tree for c in m['capitulos'] for a in c['aulas']]


def curso(db, row):
    return {'id':row.id,'titulo':row.titulo,'descricao':row.descricao,'estado':row.estado,
        'disciplina_id':row.disciplina_id,'professor_id':row.professor_id,'origem_id':row.origem_id,
        'versao':comum.versao(db,row.id)}


def recurso(row):
    return {'id':row.id,'aula_id':row.aula_id,'titulo':row.titulo,'tipo':row.tipo,
        'link':row.link,'mime':row.mime,'tamanho':row.tamanho,'estado':row.estado}


def aula(db, course_id, lesson_id, *, aluno=False):
    row = comum.aula(db,course_id,lesson_id)
    query = db.query(RecursoAulaCursoModel).filter_by(aula_id=row.id)
    if aluno:
        query = query.filter_by(estado='ativo')
    return {'id':row.id,'titulo':row.titulo,'descricao':row.descricao,'video_id':row.video_id,
        **conteudo.formato(db,row),'recursos':[recurso(r) for r in query.order_by(RecursoAulaCursoModel.id).all()]}


def aprendizagem(db, *, ator_id, oferta_id, lesson_id=None):
    base_user = comum.usuario(db,ator_id,('aluno',))
    offer,course,student = base.acesso_oferta(db,oferta_id,base_user.id,'aluno')
    tree,ids = indice(db,course.id)
    completed = {value for (value,) in db.query(ProgressoAulaModel.aula_id).filter_by(
        aluno_id=student.id,oferta_id=offer.id).all()} & set(ids)
    cursor = db.query(RetomadaCursoModel).filter_by(aluno_id=student.id,oferta_id=offer.id).first()
    current = (comum.inteiro(lesson_id) if lesson_id is not None else cursor.aula_id if cursor
        else next((value for value in ids if value not in completed),ids[0] if ids else None))
    if current is not None:
        comum.aula(db,course.id,current)
    position = ids.index(current) if current in ids else -1
    return {'oferta_id':offer.id,'curso':curso(db,course),'modulos':tree,'total':len(ids),
        'concluidas':sorted(completed),'progresso':round(100*len(completed)/len(ids)) if ids else 0,
        'retomada':{'aula_id':cursor.aula_id if cursor else None,'versao':cursor.versao if cursor else 0},
        'aula':aula(db,course.id,current,aluno=True) if current is not None else None,
        'anterior_id':ids[position-1] if position>0 else None,
        'proxima_id':ids[position+1] if 0<=position<len(ids)-1 else None}


def biblioteca(db, identity, page):
    size = 25
    if identity.papel!='aluno':
        query = db.query(CursoModel,func.coalesce(CursoVersaoModel.versao,1)).outerjoin(
            CursoVersaoModel,CursoVersaoModel.curso_id==CursoModel.id)
        if identity.papel=='professor':
            teacher = base.professor(db,identity.id)
            query = query.filter(CursoModel.professor_id==teacher.id,db.query(ProfessorDisciplinaModel.id).filter(
                ProfessorDisciplinaModel.professor_id==teacher.id,
                ProfessorDisciplinaModel.disciplina_id==CursoModel.disciplina_id).exists())
        total = query.count()
        rows = query.order_by(CursoModel.id.desc()).offset((page-1)*size).limit(size).all()
        return {'pagina':page,'por_pagina':size,'total':total,'cursos':[{'id':r.id,'titulo':r.titulo,
            'estado':r.estado,'disciplina_id':r.disciplina_id,'versao':v} for r,v in rows]}
    student = db.query(AlunoModel).filter_by(usuario_id=identity.id).first()
    if not student or str(student.status_matricula or '').strip().lower() in {
            'inativo','inativa','cancelado','cancelada','trancado','trancada'}:
        return {'pagina':page,'por_pagina':size,'total':0,'ofertas':[]}
    authorized = pairs(db,identity).with_entities(TurmaDisciplinaModel.id).subquery()
    query = db.query(OfertaCursoModel,CursoModel,TurmaModel.nome).join(CursoModel,
        CursoModel.id==OfertaCursoModel.curso_id).join(TurmaDisciplinaModel,
        TurmaDisciplinaModel.id==OfertaCursoModel.turma_disciplina_id).join(TurmaModel,
        TurmaModel.id==TurmaDisciplinaModel.turma_id).filter(OfertaCursoModel.ativa.is_(True),
        CursoModel.estado=='publicado',CursoModel.disciplina_id==TurmaDisciplinaModel.disciplina_id,
        OfertaCursoModel.turma_disciplina_id.in_(db.query(authorized.c.id)))
    total = query.count()
    rows = query.order_by(OfertaCursoModel.id).offset((page-1)*size).limit(size).all()
    course_ids,offer_ids = [c.id for o,c,t in rows],[o.id for o,c,t in rows]
    totals = dict(db.query(CapituloModel.curso_id,func.count(AulaModel.id)).join(TemaModel,
        TemaModel.capitulo_id==CapituloModel.id).join(AulaModel,AulaModel.tema_id==TemaModel.id).filter(
        CapituloModel.curso_id.in_(course_ids)).group_by(CapituloModel.curso_id).all())
    counts = dict(db.query(ProgressoAulaModel.oferta_id,func.count(ProgressoAulaModel.id)).join(
        OfertaCursoModel,OfertaCursoModel.id==ProgressoAulaModel.oferta_id).join(AulaModel,
        AulaModel.id==ProgressoAulaModel.aula_id).join(TemaModel).join(CapituloModel).filter(
        ProgressoAulaModel.aluno_id==(student.id if student else -1),ProgressoAulaModel.oferta_id.in_(offer_ids),
        CapituloModel.curso_id==OfertaCursoModel.curso_id).group_by(ProgressoAulaModel.oferta_id).all())
    return {'pagina':page,'por_pagina':size,'total':total,'ofertas':[{'id':o.id,'curso_id':c.id,
        'titulo':c.titulo,'turma':t,'turma_disciplina_id':o.turma_disciplina_id,
        'progresso':round(100*counts.get(o.id,0)/totals[c.id]) if totals.get(c.id) else 0} for o,c,t in rows]}


def continuacoes(db,aluno_id,offer_ids):
    """Destinos leves para formulários sem JS, consultados em lote por página."""
    if not offer_ids:
        return {}
    rows = db.query(OfertaCursoModel.id,AulaModel.id).join(CapituloModel,
        CapituloModel.curso_id==OfertaCursoModel.curso_id).join(TemaModel,
        TemaModel.capitulo_id==CapituloModel.id).join(AulaModel,AulaModel.tema_id==TemaModel.id).filter(
        OfertaCursoModel.id.in_(offer_ids)).order_by(OfertaCursoModel.id,CapituloModel.posicao,TemaModel.posicao,AulaModel.posicao).all()
    by_offer = {}
    for offer,lesson in rows:
        by_offer.setdefault(offer,[]).append(lesson)
    cursors = {r.oferta_id:r for r in db.query(RetomadaCursoModel).filter(
        RetomadaCursoModel.aluno_id==aluno_id,RetomadaCursoModel.oferta_id.in_(offer_ids)).all()}
    completed = set(db.query(ProgressoAulaModel.oferta_id,ProgressoAulaModel.aula_id).filter(
        ProgressoAulaModel.aluno_id==aluno_id,ProgressoAulaModel.oferta_id.in_(offer_ids)).all())
    result = {}
    for offer,ids in by_offer.items():
        cursor = cursors.get(offer)
        target = cursor.aula_id if cursor and cursor.aula_id in ids else next((a for a in ids if (offer,a) not in completed),ids[0])
        result[offer] = {'aula_id':target,'versao':cursor.versao if cursor else 0}
    return result
