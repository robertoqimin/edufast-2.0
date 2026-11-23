"""Backend MS04. API separada para manter o frontend legado até sua revisão."""
import hmac
import io
from flask import Blueprint, current_app, g, jsonify, request, session, send_file, redirect, url_for, render_template, flash
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from app.database import get_session
from app.concurrency import MutationConflict, begin_submission, finish_submission
from app.models import (CursoModel, CursoVersaoModel, ProfessorModel, ProfessorDisciplinaModel,
    DisciplinaModel, OfertaCursoModel, TurmaDisciplinaModel, RecursoAulaCursoModel,
    SolicitacaoAlteracaoModel, AlunoModel)
from app.services import cursos as base
from app.services.identidade_service import require_role
from app.services.cursos_ms04 import comum, autoria, publicacao, retomada, conteudo, leitura

cursos_api_bp = Blueprint('cursos_api',__name__,url_prefix='/api')


@cursos_api_bp.before_request
def boundary():
    g.curso_identity = require_role('admin','super_admin','professor','aluno')
    if request.method=='POST' and not request.headers.get('Authorization'):
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token','')
        if not token or not hmac.compare_digest(str(session.get('csrf_token','')),token):
            raise MutationConflict('Token CSRF obrigatório.',403)
    with get_session() as db:
        comum.habilitado(db)


@cursos_api_bp.after_request
def private(response):
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response


@cursos_api_bp.errorhandler(MutationConflict)
def conflict(error):
    if web_request():
        return render_template('curso_ms04_erro.html',error=error.message),error.status
    return jsonify(erro=error.message),error.status


@cursos_api_bp.errorhandler(HTTPException)
def http_error(error):
    if web_request():
        return render_template('curso_ms04_erro.html',error=error.description),error.code
    return jsonify(erro=error.description),error.code


@cursos_api_bp.errorhandler(IntegrityError)
def integrity(error):
    if web_request():
        return render_template('curso_ms04_erro.html',error='Conflito de gravação. Recarregue antes de tentar novamente.'),409
    return jsonify(erro='Conflito de gravação. Recarregue antes de tentar novamente.'),409


def payload():
    value = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    if not isinstance(value,dict):
        raise MutationConflict('Corpo inválido.',400)
    return value


def web_request():
    return request.args.get('interface')=='web' and not request.is_json


def result(body,code):
    if not web_request():
        return jsonify(body),code
    args = request.view_args or {}
    course_id = body.get('curso_id') or args.get('curso_id')
    lesson_id = args.get('aula_id')
    if request.endpoint=='cursos_api.editar' and request.form.get('tipo')=='aula' and request.form.get('acao')!='remover':
        lesson_id = body.get('item_id')
    destination = url_for('cursos_web.aula',curso_id=course_id,aula_id=lesson_id) if lesson_id else url_for('cursos_web.editor',curso_id=course_id)
    flash('Alteração salva.' if code!=202 else 'Solicitação enviada para revisão.','success')
    return redirect(destination,code=303)


def response(db, entry, data, status=200):
    body,code = finish_submission(db,entry,data,status)
    return result(body,code)


@cursos_api_bp.get('/cursos')
def biblioteca():
    page = comum.inteiro(request.args.get('pagina',1))
    with get_session() as db:
        return jsonify(leitura.biblioteca(db,g.curso_identity,page))


@cursos_api_bp.post('/cursos')
def criar():
    identity,data = g.curso_identity,payload()
    with get_session() as db:
        user = comum.usuario(db,identity.id)
        comum.campos(data,{'disciplina_id','professor_id','titulo','descricao'})
        entry,replay = begin_submission(db,'ms04:criar',user.id)
        if replay:
            return result(replay[0],replay[1])
        subject = base.obter(db,DisciplinaModel,comum.inteiro(data.get('disciplina_id')))
        teacher_id = base.professor(db,user.id).id if user.tipo=='professor' else comum.inteiro(data.get('professor_id'))
        if user.tipo=='professor' and 'professor_id' in data and comum.inteiro(data['professor_id'])!=teacher_id:
            raise MutationConflict('Não é permitido atribuir autoria a outro professor.',403)
        teacher = base.obter(db,ProfessorModel,teacher_id)
        comum.usuario(db,teacher.usuario_id,('professor',))
        if not db.query(ProfessorDisciplinaModel).filter_by(professor_id=teacher.id,disciplina_id=subject.id).first():
            raise MutationConflict('Vincule o professor à disciplina.',403)
        row = CursoModel(disciplina_id=subject.id,professor_id=teacher.id,titulo=base.titulo(data.get('titulo')),
            descricao=base.texto(data.get('descricao','')))
        db.add(row)
        db.flush()
        db.add(CursoVersaoModel(curso_id=row.id,versao=1))
        base.auditar(db,user.id,'ms04_criar_curso',row.id)
        return response(db,entry,{'curso_id':row.id,'versao':1,'estado':'rascunho'},201)


@cursos_api_bp.get('/cursos/<int:curso_id>')
def editor(curso_id):
    with get_session() as db:
        course = comum.autoria(db,g.curso_identity.id,curso_id)
        tree,ids = leitura.indice(db,course.id)
        pending = db.query(SolicitacaoAlteracaoModel.id).filter_by(
            recurso_pendente=f'curso:{course.id}:{comum.versao(db,course.id)}',estado='pendente').first()
        offers = db.query(OfertaCursoModel).filter_by(curso_id=course.id).order_by(OfertaCursoModel.id).all()
        return jsonify(curso=leitura.curso(db,course),modulos=tree,em_revisao=bool(pending),
            ofertas=[{'id':r.id,'turma_disciplina_id':r.turma_disciplina_id,'ativa':r.ativa} for r in offers])


@cursos_api_bp.get('/cursos/<int:curso_id>/aulas/<int:aula_id>')
def aula_autor(curso_id,aula_id):
    with get_session() as db:
        course = comum.autoria(db,g.curso_identity.id,curso_id)
        return jsonify(leitura.aula(db,course.id,aula_id))


@cursos_api_bp.post('/cursos/<int:curso_id>/estrutura')
def editar(curso_id):
    data = payload()
    with get_session() as db:
        comum.autoria(db,g.curso_identity.id,curso_id)
        entry,replay = begin_submission(db,f'ms04:editar:{curso_id}',g.curso_identity.id)
        if replay:
            return result(replay[0],replay[1])
        saved = autoria.salvar_rascunho(db,ator_id=g.curso_identity.id,curso_id=curso_id,
            versao=data.get('versao'),dados=data)
        return response(db,entry,saved)


@cursos_api_bp.post('/cursos/<int:curso_id>/duplicar')
def duplicar(curso_id):
    data = payload()
    comum.campos(data,{'versao'})
    with get_session() as db:
        comum.autoria(db,g.curso_identity.id,curso_id)
        entry,replay = begin_submission(db,f'ms04:duplicar:{curso_id}',g.curso_identity.id)
        if replay:
            return result(replay[0],replay[1])
        return response(db,entry,autoria.duplicar_edicao(db,ator_id=g.curso_identity.id,curso_id=curso_id,payload=data),201)


@cursos_api_bp.post('/cursos/<int:curso_id>/solicitar-publicacao')
def solicitar_publicacao(curso_id):
    data = payload()
    comum.campos(data,{'versao'})
    from app.services.aprovacoes_service import submit_proposal
    body,status = submit_proposal('publicar_curso',{'curso_id':curso_id,'versao':data.get('versao')})
    return result(body,status)


@cursos_api_bp.post('/cursos/<int:curso_id>/estado')
def estado(curso_id):
    data = payload()
    comum.campos(data,{'versao','estado'})
    with get_session() as db:
        user = comum.usuario(db,g.curso_identity.id,('admin','super_admin'))
        course = comum.autoria(db,user.id,curso_id)
        entry,replay = begin_submission(db,f'ms04:estado:{curso_id}',user.id)
        if replay:
            return result(replay[0],replay[1])
        revision = comum.revisao(db,course.id)
        comum.exigir_versao(revision,data)
        target = data.get('estado')
        if target=='publicado' and course.estado=='rascunho':
            publicacao.snapshot(db,course)
        elif target!='arquivado' or course.estado=='arquivado':
            raise MutationConflict('Transição de estado não permitida.')
        course.estado = target
        base.auditar(db,user.id,'ms04_'+target,course.id)
        return response(db,entry,{'curso_id':course.id,'estado':course.estado,'versao':revision.versao})


@cursos_api_bp.post('/cursos/<int:curso_id>/ofertas')
def ofertar(curso_id):
    data = payload()
    comum.campos(data,{'versao','turma_disciplina_id','ativa'})
    with get_session() as db:
        user = comum.usuario(db,g.curso_identity.id,('admin','super_admin'))
        course = comum.autoria(db,user.id,curso_id)
        entry,replay = begin_submission(db,f'ms04:ofertar:{curso_id}',user.id)
        if replay:
            return result(replay[0],replay[1])
        revision = comum.revisao(db,course.id)
        comum.exigir_versao(revision,data)
        pair = base.obter(db,TurmaDisciplinaModel,comum.inteiro(data.get('turma_disciplina_id')))
        active = data.get('ativa',True)
        if web_request() and active in {'true','false'}:
            active = active=='true'
        if not isinstance(active,bool):
            raise MutationConflict('Informe ativa como booleano JSON.',400)
        if pair.disciplina_id!=course.disciplina_id or not base.turma_ativa(db,pair.turma_id):
            raise MutationConflict('Oferta incompatível com a disciplina ou turma.',404)
        if course.estado!='publicado':
            raise MutationConflict('Publique o curso antes de alterar ofertas.')
        row = db.query(OfertaCursoModel).filter_by(curso_id=course.id,turma_disciplina_id=pair.id).first()
        if not row:
            if not active:
                raise MutationConflict('Oferta não encontrada.',404)
            row = OfertaCursoModel(curso_id=course.id,turma_disciplina_id=pair.id,ativa=active)
            db.add(row)
        row.ativa = active
        db.flush()
        base.auditar(db,user.id,'ms04_oferta',row.id)
        return response(db,entry,{'id':row.id,'ativa':row.ativa,'versao':revision.versao})


@cursos_api_bp.get('/aprender/<int:oferta_id>')
def aprender(oferta_id):
    with get_session() as db:
        return jsonify(leitura.aprendizagem(db,ator_id=g.curso_identity.id,oferta_id=oferta_id,lesson_id=request.args.get('aula')))


@cursos_api_bp.get('/aprender/<int:oferta_id>/retomada')
def consultar_retomada(oferta_id):
    with get_session() as db:
        from app.models import RetomadaCursoModel
        user = comum.usuario(db,g.curso_identity.id,('aluno',))
        offer,course,student = base.acesso_oferta(db,oferta_id,user.id,'aluno')
        row = db.query(RetomadaCursoModel).filter_by(aluno_id=student.id,oferta_id=offer.id).first()
        if row:
            comum.aula(db,course.id,row.aula_id)
        return jsonify(aula_id=row.aula_id if row else None,versao=row.versao if row else 0)


@cursos_api_bp.post('/aprender/<int:oferta_id>/aulas/<int:aula_id>/abrir',defaults={'action':'abrir'})
@cursos_api_bp.post('/aprender/<int:oferta_id>/aulas/<int:aula_id>/concluir',defaults={'action':'concluir'})
def progresso(oferta_id,aula_id,action):
    if action not in {'abrir','concluir'}:
        raise MutationConflict('Operação não encontrada.',404)
    data = payload()
    comum.campos(data,{'versao'} if action=='abrir' else set())
    with get_session() as db:
        user = comum.usuario(db,g.curso_identity.id,('aluno',))
        offer,course,student = base.acesso_oferta(db,oferta_id,user.id,'aluno')
        comum.aula(db,course.id,aula_id)
        entry,replay = begin_submission(db,f'ms04:{action}:{oferta_id}:{aula_id}',user.id)
        if replay:
            body,code = replay
        else:
            body = (retomada.registrar_abertura(db,ator_id=user.id,oferta_id=oferta_id,aula_id=aula_id,versao=data.get('versao'))
                if action=='abrir' else retomada.concluir(db,ator_id=user.id,oferta_id=oferta_id,aula_id=aula_id))
            body['destino'] = f'/api/aprender/{oferta_id}?aula={aula_id}'
            body,code = finish_submission(db,entry,body,200)
        if not request.is_json:
            if web_request():
                return redirect(url_for('cursos_web.aprender',oferta_id=oferta_id,aula=aula_id),code=303)
            return redirect(body['destino'],code=303)
        return jsonify(body),code


@cursos_api_bp.post('/cursos/<int:curso_id>/aulas/<int:aula_id>/recursos')
def adicionar_recurso(curso_id,aula_id):
    data = payload()
    comum.campos(data,{'tipo','titulo','link','versao'})
    if set(request.files)-{'arquivo'} or len(request.files.getlist('arquivo'))>1:
        raise MutationConflict('Envie somente um arquivo por recurso.',400)
    path = None
    try:
        with get_session() as db:
            comum.autoria(db,g.curso_identity.id,curso_id)
            entry,replay = begin_submission(db,f'ms04:recurso:{curso_id}:{aula_id}',g.curso_identity.id)
            if replay:
                return result(replay[0],replay[1])
            row,revision,path = conteudo.novo_recurso(db,ator_id=g.curso_identity.id,curso_id=curso_id,aula_id=aula_id,
                payload=data,upload=request.files.get('arquivo'))
            saved = response(db,entry,{'recurso':leitura.recurso(row),'versao':revision.versao},201)
            path = None
            return saved
    finally:
        if path:
            path.unlink(missing_ok=True)


@cursos_api_bp.post('/cursos/<int:curso_id>/aulas/<int:aula_id>/recursos/<int:recurso_id>/arquivar')
def arquivar_recurso(curso_id,aula_id,recurso_id):
    data = payload()
    comum.campos(data,{'versao'})
    with get_session() as db:
        course = comum.autoria(db,g.curso_identity.id,curso_id,editar=True)
        comum.aula(db,course.id,aula_id)
        entry,replay = begin_submission(db,f'ms04:arquivar_recurso:{curso_id}:{aula_id}:{recurso_id}',g.curso_identity.id)
        if replay:
            return result(replay[0],replay[1])
        row = db.query(RecursoAulaCursoModel).filter_by(id=recurso_id,aula_id=aula_id,estado='ativo').first()
        if not row:
            raise MutationConflict('Recurso não encontrado.',404)
        revision = comum.revisao(db,course.id)
        comum.exigir_versao(revision,data)
        row.estado = 'arquivado'
        base.auditar(db,g.curso_identity.id,'ms04_arquivar_recurso',row.id)
        return response(db,entry,{'id':row.id,'estado':row.estado,'versao':revision.versao})


@cursos_api_bp.get('/aprender/<int:oferta_id>/aulas/<int:aula_id>/recursos/<int:recurso_id>/arquivo')
def arquivo(oferta_id,aula_id,recurso_id):
    with get_session() as db:
        user = comum.usuario(db,g.curso_identity.id,('aluno',))
        offer,course,student = base.acesso_oferta(db,oferta_id,user.id,'aluno')
        comum.aula(db,course.id,aula_id)
        row = db.query(RecursoAulaCursoModel).filter_by(id=recurso_id,aula_id=aula_id,tipo='arquivo',estado='ativo').first()
        if not row:
            raise MutationConflict('Recurso não encontrado.',404)
        data = conteudo.ler_arquivo(row)
        base.auditar(db,user.id,'ms04_baixar_recurso',f'{offer.id}:{row.id}')
        db.commit()
        ext = {'application/pdf':'.pdf','image/png':'.png','image/jpeg':'.jpg'}[row.mime]
        return send_file(io.BytesIO(data),mimetype=row.mime,as_attachment=True,download_name=(secure_filename(row.titulo) or 'material')+ext)


@cursos_api_bp.get('/cursos/<int:curso_id>/aulas/<int:aula_id>/recursos/<int:recurso_id>/arquivo')
def arquivo_autor(curso_id,aula_id,recurso_id):
    with get_session() as db:
        course = comum.autoria(db,g.curso_identity.id,curso_id)
        comum.aula(db,course.id,aula_id)
        row = db.query(RecursoAulaCursoModel).filter_by(id=recurso_id,aula_id=aula_id,tipo='arquivo').first()
        if not row:
            raise MutationConflict('Recurso não encontrado.',404)
        data = conteudo.ler_arquivo(row)
        base.auditar(db,g.curso_identity.id,'ms04_conferir_recurso',row.id)
        db.commit()
        ext = {'application/pdf':'.pdf','image/png':'.png','image/jpeg':'.jpg'}[row.mime]
        return send_file(io.BytesIO(data),mimetype=row.mime,as_attachment=True,download_name=(secure_filename(row.titulo) or 'material')+ext)


@cursos_api_bp.get('/estudos/disciplinas/<int:pair_id>/cursos')
def cursos_disciplina(pair_id):
    from app.services.estudo_service import pair_access
    page = comum.inteiro(request.args.get('pagina',1))
    with get_session() as db:
        pair_access(db,g.curso_identity,pair_id)
        if g.curso_identity.papel=='aluno':
            student = db.query(AlunoModel).filter_by(usuario_id=g.curso_identity.id).first()
            if str(student.status_matricula or '').strip().lower() in {'inativo','inativa','cancelado','cancelada','trancado','trancada'}:
                raise MutationConflict('Disciplina não encontrada.',404)
        query = db.query(OfertaCursoModel,CursoModel).join(CursoModel,CursoModel.id==OfertaCursoModel.curso_id).join(
            TurmaDisciplinaModel,TurmaDisciplinaModel.id==OfertaCursoModel.turma_disciplina_id).filter(
            OfertaCursoModel.turma_disciplina_id==pair_id,OfertaCursoModel.ativa.is_(True),CursoModel.estado=='publicado',
            CursoModel.disciplina_id==TurmaDisciplinaModel.disciplina_id)
        total = query.count()
        rows = query.order_by(OfertaCursoModel.id).offset((page-1)*25).limit(25).all()
        return jsonify(pagina=page,por_pagina=25,total=total,ofertas=[{
            'id':o.id,'curso_id':c.id,'titulo':c.titulo,'turma_disciplina_id':pair_id,
            'aprendizagem':f'/api/aprender/{o.id}'} for o,c in rows])
