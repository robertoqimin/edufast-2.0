"""Interface HTML do MS04; gravações usam os endpoints e guardas da API."""
from flask import Blueprint, render_template, request, g
from sqlalchemy import or_
from app.database import get_session
from app.concurrency import MutationConflict
from app.models import (DisciplinaModel, ProfessorModel, ProfessorDisciplinaModel, UsuarioModel,
    TurmaModel, TurmaDisciplinaModel, EstadoTurmaModel, SolicitacaoAlteracaoModel,
    OfertaCursoModel, TemaModel, CapituloModel, AlunoModel)
from app.services.identidade_service import require_role
from app.services import cursos as base
from app.services.cursos_ms04 import comum, leitura

cursos_web_bp = Blueprint('cursos_web',__name__,url_prefix='/aprendizagem')


@cursos_web_bp.before_request
def boundary():
    g.curso_web_identity = require_role('admin','super_admin','professor','aluno')
    with get_session() as db:
        comum.habilitado(db)


@cursos_web_bp.after_request
def private(response):
    response.headers['Cache-Control']='no-store'
    return response


@cursos_web_bp.errorhandler(MutationConflict)
def error(exc):
    return render_template('curso_ms04_erro.html',error=exc.message),exc.status


def render_biblioteca(db,identity):
    page = comum.inteiro(request.args.get('pagina',1))
    data = leitura.biblioteca(db,identity,page)
    subjects,teachers = [],[]
    if identity.papel=='aluno':
        student = db.query(AlunoModel).filter_by(usuario_id=identity.id).first()
        choices = leitura.continuacoes(db,student.id,[r['id'] for r in data['ofertas']]) if student else {}
        for row in data['ofertas']:
            row['continuacao'] = choices.get(row['id'])
    else:
        query = db.query(DisciplinaModel)
        if identity.papel=='professor':
            teacher = base.professor(db,identity.id)
            query = query.join(ProfessorDisciplinaModel).filter(ProfessorDisciplinaModel.professor_id==teacher.id)
        else:
            teachers = db.query(ProfessorModel).join(UsuarioModel).filter(UsuarioModel.tipo=='professor',UsuarioModel.estado=='ativo').order_by(ProfessorModel.nome).all()
        subjects = query.order_by(DisciplinaModel.nome).all()
    return render_template('curso_ms04_biblioteca.html',identity=identity,data=data,disciplinas=subjects,professores=teachers)


def render_editor(db,identity,curso_id):
    course = comum.autoria(db,identity.id,curso_id)
    version = comum.versao(db,course.id)
    tree,ids = leitura.indice(db,course.id)
    pending = db.query(SolicitacaoAlteracaoModel).filter_by(tipo='publicar_curso',estado='pendente').filter(
        SolicitacaoAlteracaoModel.recurso_pendente.like(f'curso:{course.id}:%')).all()
    current = any(row.recurso_pendente==f'curso:{course.id}:{version}' for row in pending)
    offers = db.query(OfertaCursoModel,TurmaModel).join(TurmaDisciplinaModel,
        TurmaDisciplinaModel.id==OfertaCursoModel.turma_disciplina_id).join(TurmaModel,
        TurmaModel.id==TurmaDisciplinaModel.turma_id).filter(OfertaCursoModel.curso_id==course.id).all()
    pairs = db.query(TurmaDisciplinaModel,TurmaModel).join(TurmaModel).outerjoin(EstadoTurmaModel,
        EstadoTurmaModel.turma_id==TurmaModel.id).filter(TurmaDisciplinaModel.disciplina_id==course.disciplina_id,
        or_(EstadoTurmaModel.arquivada.is_(False),EstadoTurmaModel.turma_id.is_(None))).order_by(TurmaModel.nome).all() if identity.admin else []
    return render_template('curso_ms04_editor.html',identity=identity,curso=leitura.curso(db,course),
        disciplina=base.obter(db,DisciplinaModel,course.disciplina_id),modulos=tree,total=len(ids),
        em_revisao=current,revisao_antiga=bool(pending) and not current,ofertas=offers,pares=pairs)


def render_aprender(db,identity,oferta_id):
    data = leitura.aprendizagem(db,ator_id=identity.id,oferta_id=oferta_id,lesson_id=request.args.get('aula'))
    row = data['aula']
    opening = row is not None and data['retomada']['aula_id']!=row['id']
    return render_template('curso_ms04_aprender.html',identity=identity,data=data,precisa_abrir=opening,
        youtube_url='https://www.youtube.com/watch?v='+row['video_id'] if row and row['video_id'] else None)


@cursos_web_bp.get('')
def biblioteca():
    with get_session() as db:
        return render_biblioteca(db,g.curso_web_identity)


@cursos_web_bp.get('/cursos/<int:curso_id>')
def editor(curso_id):
    with get_session() as db:
        return render_editor(db,g.curso_web_identity,curso_id)


@cursos_web_bp.get('/cursos/<int:curso_id>/capitulos/<int:capitulo_id>/aulas/nova')
@cursos_web_bp.get('/cursos/<int:curso_id>/aulas/<int:aula_id>')
def aula(curso_id,capitulo_id=None,aula_id=None):
    identity = g.curso_web_identity
    with get_session() as db:
        course = comum.autoria(db,identity.id,curso_id,editar=aula_id is None)
        if aula_id is not None:
            row = leitura.aula(db,course.id,aula_id)
            chapter_id = comum.aula(db,course.id,aula_id).tema_id
        else:
            chapter = db.query(TemaModel).join(CapituloModel).filter(TemaModel.id==capitulo_id,CapituloModel.curso_id==course.id).first()
            if not chapter:
                raise MutationConflict('Capítulo não encontrado neste curso.',404)
            chapter_id = chapter.id
            kind = request.args.get('tipo','texto')
            if kind not in {'texto','video'}:
                raise MutationConflict('Tipo de aula inválido.',400)
            row = {'tipo':kind,'titulo':'','descricao':'','corpo':'','video_id':None,'recursos':[]}
        return render_template('curso_ms04_aula.html',identity=identity,curso=leitura.curso(db,course),
            aula=row,capitulo_id=chapter_id,nova=aula_id is None,
            youtube_url='https://www.youtube.com/watch?v='+row['video_id'] if row['video_id'] else None)


@cursos_web_bp.get('/ofertas/<int:oferta_id>')
def aprender(oferta_id):
    with get_session() as db:
        return render_aprender(db,g.curso_web_identity,oferta_id)


@cursos_web_bp.get('/disciplinas/<int:pair_id>')
def disciplina(pair_id):
    from app.services.estudo_service import pair_access
    identity = g.curso_web_identity
    with get_session() as db:
        pair,turma,subject = pair_access(db,identity,pair_id)
        query = db.query(OfertaCursoModel,base.CursoModel).join(base.CursoModel,
            base.CursoModel.id==OfertaCursoModel.curso_id).filter(OfertaCursoModel.turma_disciplina_id==pair.id,
            OfertaCursoModel.ativa.is_(True),base.CursoModel.estado=='publicado',base.CursoModel.disciplina_id==pair.disciplina_id)
        page = comum.inteiro(request.args.get('pagina',1))
        total = query.count()
        rows = query.order_by(OfertaCursoModel.id).offset((page-1)*25).limit(25).all()
        choices = {}
        if identity.papel=='aluno':
            student = db.query(AlunoModel).filter_by(usuario_id=identity.id).first()
            if str(student.status_matricula or '').strip().lower() in {'inativo','inativa','cancelado','cancelada','trancado','trancada'}:
                raise MutationConflict('Disciplina não encontrada.',404)
            choices = leitura.continuacoes(db,student.id,[o.id for o,c in rows])
        return render_template('curso_ms04_disciplina.html',identity=identity,pair=pair,turma=turma,
            disciplina=subject,rows=rows,continuacoes=choices,page=page,total=total)
