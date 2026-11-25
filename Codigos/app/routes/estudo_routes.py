"""Espaço da disciplina: rascunhos docentes, revisão e material privado."""
import hmac
import io
from pathlib import Path
from uuid import uuid4
from cryptography.fernet import InvalidToken
from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from sqlalchemy import distinct, func, inspect, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
from app.concurrency import MutationConflict, begin_submission, check_version, finish_submission
from app.database import engine, get_session
from app.models import (AuditoriaEstudoModel, ConteudoEstudoModel, SolicitacaoAlteracaoModel, TurmaModel,
    DisciplinaModel, SecaoEstudoModel, ConteudoSecaoEstudoModel)
from app.services.identidade_service import require_role
from app.services import estudo_service as service
from app.services import leitor, video_envio
from config import caminho_uploads

estudo_bp = Blueprint('estudos', __name__)
TABLES = {'estudo_conteudos', 'estudo_auditoria'}


@estudo_bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


def wants_json():
    return request.is_json or request.args.get('formato') == 'json'


@estudo_bp.errorhandler(MutationConflict)
def conflict(exc):
    if wants_json():
        return jsonify(erro=exc.message), exc.status
    return render_template('estudo_erro.html', mensagem=exc.message), exc.status


@estudo_bp.errorhandler(IntegrityError)
def integrity(exc):
    return conflict(MutationConflict('Outro envio alterou o conteúdo. Reabra a página antes de tentar novamente.'))


@estudo_bp.before_request
def boundary():
    g.estudo_identity = require_role('admin','super_admin','professor','aluno')
    if request.method == 'POST' and not request.headers.get('Authorization'):
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token','')
        if not token or not hmac.compare_digest(str(session.get('csrf_token','')),token):
            raise MutationConflict('Recarregue o formulário para confirmar seu envio.',403)
    if not TABLES <= set(inspect(engine).get_table_names()):
        raise MutationConflict('O espaço da disciplina ainda não foi habilitado nesta instalação. Os dados atuais estão preservados.',503)


def data():
    value = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    if not isinstance(value,dict):
        raise MutationConflict('Dados inválidos.',400)
    return value


def result(body, status=200, *, content_id=None):
    if wants_json():
        return jsonify(body), status
    flash(body.get('mensagem','Conteúdo salvo.'),'success')
    return redirect(url_for('estudos.conteudo', content_id=content_id))


def page_number():
    return service.integer(request.args.get('pagina',1))


def pending(db, row):
    return db.query(SolicitacaoAlteracaoModel.id).filter_by(
        recurso_pendente=f'estudo:{row.id}:{row.versao}', estado='pendente').first() is not None


@estudo_bp.get('/estudos')
def disciplinas():
    identity, page = g.estudo_identity, page_number()
    with get_session() as db:
        query = service.pairs(db,identity)
        total = query.count()
        rows = query.order_by(TurmaModel.ano_letivo.desc(),TurmaModel.nome,DisciplinaModel.nome,
            service.TurmaDisciplinaModel.id).offset((page-1)*service.PAGE_SIZE).limit(service.PAGE_SIZE).all()
        if wants_json():
            return jsonify(total=total,pagina=page,disciplinas=[{'id':p.id,'turma':t.nome,
                'disciplina':d.nome,'ano':t.ano_letivo} for p,t,d in rows])
        return render_template('estudo_disciplinas.html',rows=rows,total=total,page=page,
            has_next=page*service.PAGE_SIZE<total)


def consulta_aba(db, identity, pair_id, section, tab, enabled):
    """Conteúdos que esta pessoa vê em uma aba (lista da disciplina e anterior/próximo)."""
    query = db.query(ConteudoEstudoModel).filter_by(turma_disciplina_id=pair_id)
    if section:
        query = query.join(ConteudoSecaoEstudoModel,ConteudoSecaoEstudoModel.conteudo_id == ConteudoEstudoModel.id).filter(ConteudoSecaoEstudoModel.secao_id == section.id)
    else:
        query = query.filter(ConteudoEstudoModel.tipo == 'aviso' if tab == 'avisos' else ConteudoEstudoModel.tipo.in_(['link','arquivo']))
        if enabled:
            query = query.filter(~db.query(ConteudoSecaoEstudoModel.conteudo_id).filter(
                ConteudoSecaoEstudoModel.conteudo_id == ConteudoEstudoModel.id).exists())
    if not identity.admin:
        query = query.filter(or_(ConteudoEstudoModel.estado == 'publicado',ConteudoEstudoModel.autor_id == identity.id)
            if identity.papel == 'professor' else ConteudoEstudoModel.estado == 'publicado')
    return query


def vizinhos(db, identity, row, section):
    """Material anterior e próximo na ordem da lista (mais recente primeiro) e a posição deste."""
    tab = None if section else ('avisos' if row.tipo == 'aviso' else 'materiais')
    query = consulta_aba(db,identity,row.turma_disciplina_id,section,tab,service.sections_enabled(db))
    ids = ConteudoEstudoModel.id
    anterior = query.filter(ids > row.id).order_by(ids.asc()).with_entities(ids).first()
    proximo = query.filter(ids < row.id).order_by(ids.desc()).with_entities(ids).first()
    antes = query.filter(ids > row.id).count()
    return {'anterior': anterior and anterior[0], 'proximo': proximo and proximo[0],
            'posicao': antes + 1, 'total': antes + 1 + query.filter(ids < row.id).count()}


@estudo_bp.get('/estudos/disciplinas/<int:pair_id>')
def disciplina(pair_id):
    identity, page = g.estudo_identity, page_number()
    tab = request.args.get('aba','avisos')
    with get_session() as db:
        pair, classroom, subject = service.pair_access(db,identity,pair_id)
        enabled = service.sections_enabled(db)
        section = None
        if tab not in {'avisos','materiais'}:
            if not tab.startswith('secao-'):
                raise MutationConflict('Selecione uma aba da disciplina.',400)
            section = service.section_access(db,identity,tab[6:])
            if section.turma_disciplina_id != pair.id:
                raise MutationConflict('Aba não encontrada nesta disciplina.',404)
        query = consulta_aba(db,identity,pair.id,section,tab,enabled)
        total = query.count()
        rows = query.order_by(ConteudoEstudoModel.id.desc()).offset((page-1)*service.PAGE_SIZE).limit(service.PAGE_SIZE).all()
        tabs = service.sections(db,pair.id) if enabled else []
        if wants_json():
            return jsonify(total=total,pagina=page,abas=[{'id':r.id,'nome':r.nome,'ordem':r.ordem,'estado':r.estado,'versao':r.versao} for r in tabs],conteudos=[{'id':r.id,'titulo':r.titulo,'tipo':r.tipo,'estado':r.estado} for r in rows])
        from app.services.cursos_ms04.comum import habilitado as cursos_habilitados
        # U1/O6: quem envia vê o que aguarda a secretaria, não só "rascunho".
        aguardando = set()
        if identity.papel != 'aluno' and rows:
            from app.models import SolicitacaoAlteracaoModel
            for recurso, in db.query(SolicitacaoAlteracaoModel.recurso_pendente).filter(
                    SolicitacaoAlteracaoModel.tipo == 'publicar_material', SolicitacaoAlteracaoModel.estado == 'pendente',
                    SolicitacaoAlteracaoModel.recurso_pendente.in_([f'estudo:{r.id}:{r.versao}' for r in rows])):
                aguardando.add(int(recurso.split(':')[1]))
        # U2/O7: o aluno vê o que já estudou e quanto falta na aba.
        vistos, total_vistos = set(), 0
        if identity.papel == 'aluno' and rows:
            vistos = {i for i, in db.query(AuditoriaEstudoModel.conteudo_id).filter(
                AuditoriaEstudoModel.ator_id == identity.id, AuditoriaEstudoModel.acao == 'visualizar',
                AuditoriaEstudoModel.conteudo_id.in_([r.id for r in rows])).distinct()}
            total_vistos = db.query(func.count(distinct(AuditoriaEstudoModel.conteudo_id))).filter(
                AuditoriaEstudoModel.ator_id == identity.id, AuditoriaEstudoModel.acao == 'visualizar',
                AuditoriaEstudoModel.conteudo_id.in_(query.with_entities(ConteudoEstudoModel.id))).scalar()
        return render_template('estudo_disciplina.html',pair=pair,turma=classroom,disciplina=subject,aguardando=aguardando,
            vistos=vistos,total_vistos=total_vistos,
            cursos_enabled=cursos_habilitados(db,required=False),
            rows=rows,tab=tab,page=page,total=total,has_next=page*service.PAGE_SIZE<total,identity=identity,
            sections=tabs,section=section,sections_enabled=enabled)


@estudo_bp.route('/estudos/disciplinas/<int:pair_id>/novo', methods=['GET','POST'])
def novo(pair_id):
    identity = g.estudo_identity
    if identity.papel not in {'professor','admin','super_admin'}:
        raise MutationConflict('Somente docentes e administração preparam conteúdo.',403)
    target = envio = None
    try:
        with get_session() as db:
            pair, classroom, subject = service.pair_access(db,identity,pair_id)
            if request.method == 'GET':
                tabs = service.sections(db,pair.id) if service.sections_enabled(db) else []
                tabs = [r for r in tabs if identity.admin or r.autor_id == identity.id]
                return render_template('estudo_formulario.html',row=None,pair=pair,turma=classroom,disciplina=subject,
                    sections=tabs,selected_section=request.args.get('secao_id',''))
            payload = data()
            entry, replay = begin_submission(db,f'estudo:criar:{pair.id}',identity.id)
            if replay:
                return result(*replay,content_id=replay[0]['id'])
            values = service.fields(payload)
            upload = request.files.get('arquivo')
            envio = payload.get('envio_video') or None
            if envio and (values['tipo'] != 'arquivo' or upload):
                raise MutationConflict('Envie o vídeo ou um arquivo, não os dois.',400)
            if envio:
                # U2b: vídeo já enviado em partes e cifrado em blocos; só muda de pasta.
                uploads = caminho_uploads(current_app.config["UPLOAD_FOLDER"])
                target,metadata = video_envio.consumir(uploads,envio,identity.id,Path(uploads)/'materiais_estudo')
                values.update(metadata)
            elif values['tipo'] == 'arquivo':
                from app.crypto import FILE_PREFIX, cipher
                if not upload:
                    raise MutationConflict('Anexe PDF, PNG ou JPEG de até 5 MiB.',400)
                content = upload.stream.read(5*1024*1024+1)
                mime = ('application/pdf' if content.startswith(b'%PDF-') else 'image/png' if content.startswith(b'\x89PNG\r\n\x1a\n')
                    else 'image/jpeg' if content.startswith(b'\xff\xd8\xff') else None)
                if not mime or len(content)>5*1024*1024:
                    raise MutationConflict('Arquivo inválido. Use PDF, PNG ou JPEG de até 5 MiB.',400)
                try:
                    encrypted = FILE_PREFIX+cipher().encrypt(content)
                except (ValueError,UnicodeError):
                    raise MutationConflict('O envio de arquivos está temporariamente indisponível. Avise a administração.',503)
                filename = uuid4().hex+'.enc'
                folder = Path(caminho_uploads(current_app.config["UPLOAD_FOLDER"]))/'materiais_estudo'
                folder.mkdir(parents=True,exist_ok=True,mode=0o700)
                target = folder/filename
                with target.open('xb') as file:
                    file.write(encrypted)
                target.chmod(0o600)
                values.update(arquivo=filename,mime=mime,tamanho=len(content))
            elif upload:
                raise MutationConflict('Escolha o tipo Arquivo para anexar um material.',400)
            row = ConteudoEstudoModel(turma_disciplina_id=pair.id,autor_id=identity.id,**values)
            db.add(row)
            db.flush()
            service.assign_section(db,identity,row,payload.get('secao_id'))
            service.audit(db,row,identity.id,'criar_rascunho')
            response = finish_submission(db,entry,{'id':row.id,'versao':row.versao,'estado':row.estado,
                'mensagem':'Rascunho salvo. Confira o conteúdo antes de enviar para publicação.'},201)
            target = None
            if envio:
                video_envio.finalizar(caminho_uploads(current_app.config["UPLOAD_FOLDER"]),envio,identity.id)
            return result(*response,content_id=row.id)
    finally:
        if target and target.exists():
            if envio:
                video_envio.devolver(caminho_uploads(current_app.config["UPLOAD_FOLDER"]),envio,identity.id,target)
            else:
                target.unlink()


@estudo_bp.get('/estudos/conteudos/<int:content_id>')
def conteudo(content_id):
    identity = g.estudo_identity
    with get_session() as db:
        row = service.content_access(db,identity,content_id)
        section = service.content_section(db,identity,row)
        pair, classroom, subject = service.pair_access(db,identity,row.turma_disciplina_id)
        if wants_json():
            return jsonify(id=row.id,titulo=row.titulo,texto=row.texto,tipo=row.tipo,link=row.link,
                estado=row.estado,versao=row.versao,turma_disciplina_id=pair.id)
        # U2/O7: abrir o material conta como visto (uma vez por aluno) e o leitor fica na página.
        visto = False
        if identity.papel == 'aluno' and row.estado == 'publicado':
            visto = db.query(AuditoriaEstudoModel.id).filter_by(conteudo_id=row.id,ator_id=identity.id,acao='visualizar').first() is not None
            if not visto:
                service.audit(db,row,identity.id,'visualizar')
                db.commit()
        return render_template('estudo_conteudo.html',row=row,pair=pair,turma=classroom,disciplina=subject,
            identity=identity,section=section,pending=pending(db,row),visto_antes=visto,
            navegacao=vizinhos(db,identity,row,section),video=leitor.youtube(row.link) if row.tipo=='link' else None,
            can_edit=identity.admin or (identity.papel=='professor' and identity.id==row.autor_id))


@estudo_bp.route('/estudos/conteudos/<int:content_id>/editar', methods=['GET','POST'])
def editar(content_id):
    identity = g.estudo_identity
    with get_session() as db:
        row = service.content_access(db,identity,content_id,edit=True)
        service.content_section(db,identity,row,active=True)
        if row.estado != 'rascunho':
            raise MutationConflict('Conteúdo publicado ou arquivado é preservado. Prepare outro rascunho para uma nova edição.')
        pair,classroom,subject = service.pair_access(db,identity,row.turma_disciplina_id)
        if request.method == 'GET':
            return render_template('estudo_formulario.html',row=row,pair=pair,turma=classroom,disciplina=subject)
        payload = data()
        entry,replay = begin_submission(db,f'estudo:editar:{row.id}',identity.id)
        if replay:
            return result(*replay,content_id=row.id)
        values = service.fields(payload,kind=row.tipo)
        if request.files:
            raise MutationConflict('O arquivo original é preservado. Crie outro rascunho para substituí-lo.',400)
        check_version(row,payload)
        row.titulo,row.texto,row.link = values['titulo'],values['texto'],values['link']
        service.audit(db,row,identity.id,'editar_rascunho')
        return result(*finish_submission(db,entry,{'id':row.id,'versao':row.versao,'mensagem':'Rascunho atualizado.'},200),content_id=row.id)


@estudo_bp.post('/estudos/conteudos/<int:content_id>/publicar')
def publicar(content_id):
    identity, payload = g.estudo_identity, data()
    if identity.papel == 'professor':
        from app.services.aprovacoes_service import submit_proposal
        body,status = submit_proposal('publicar_material',{'conteudo_id':content_id,'versao':payload.get('versao')})
        body['mensagem'] = 'Conteúdo enviado para revisão. Os alunos terão acesso após a aprovação.'
        return result(body,status,content_id=content_id)
    if not identity.admin:
        raise MutationConflict('Acesso não autorizado.',403)
    with get_session() as db:
        row = service.content_access(db,identity,content_id,edit=True)
        entry,replay = begin_submission(db,f'estudo:publicar:{row.id}',identity.id)
        if replay:
            return result(*replay,content_id=row.id)
        if row.estado != 'rascunho':
            raise MutationConflict('O conteúdo não está em rascunho.')
        service.content_section(db,identity,row,active=True)
        check_version(row,payload)
        row.estado = 'publicado'
        service.audit(db,row,identity.id,'publicar')
        return result(*finish_submission(db,entry,{'id':row.id,'estado':row.estado,'versao':row.versao,'mensagem':'Conteúdo publicado para a turma.'},200),content_id=row.id)


@estudo_bp.post('/estudos/conteudos/<int:content_id>/arquivar')
def arquivar(content_id):
    identity,payload = g.estudo_identity,data()
    with get_session() as db:
        row = service.content_access(db,identity,content_id,edit=True)
        entry,replay = begin_submission(db,f'estudo:arquivar:{row.id}',identity.id)
        if replay:
            return result(*replay,content_id=row.id)
        if row.estado == 'arquivado':
            raise MutationConflict('Conteúdo já arquivado.')
        check_version(row,payload)
        row.estado = 'arquivado'
        service.audit(db,row,identity.id,'arquivar')
        return result(*finish_submission(db,entry,{'id':row.id,'estado':row.estado,'mensagem':'Conteúdo arquivado. O histórico foi preservado.'},200),content_id=row.id)


@estudo_bp.get('/estudos/conteudos/<int:content_id>/arquivo')
def arquivo(content_id):
    from app.crypto import FILE_PREFIX,cipher
    identity = g.estudo_identity
    with get_session() as db:
        row = service.content_access(db,identity,content_id)
        if row.tipo != 'arquivo' or not row.arquivo or len(row.arquivo)!=36 or not row.arquivo.endswith('.enc') or any(c not in '0123456789abcdef' for c in row.arquivo[:-4]):
            raise MutationConflict('Arquivo não encontrado.',404)
        source = Path(caminho_uploads(current_app.config["UPLOAD_FOLDER"]))/'materiais_estudo'/row.arquivo
        if not source.is_file():
            raise MutationConflict('Arquivo indisponível.',404)
        if video_envio.eh_video(row.mime):
            # U2b: vídeo cifrado em blocos, servido por partes (o player pede só o trecho assistido).
            if video_envio.primeira_leitura():
                service.audit(db,row,identity.id,'ler_arquivo' if leitor.modo_leitura() else 'baixar_arquivo')
                db.commit()
            return video_envio.responder(source,row.mime,row.tamanho,(secure_filename(row.titulo) or 'video')+video_envio.MIMES[row.mime])
        if source.stat().st_size>8*1024*1024:
            raise MutationConflict('Arquivo indisponível. Avise a administração.',409)
        encoded = source.read_bytes()
        if not encoded.startswith(FILE_PREFIX):
            raise MutationConflict('Arquivo indisponível. Avise a administração.',409)
        try:
            content = cipher().decrypt(encoded[len(FILE_PREFIX):])
        except (InvalidToken,ValueError,UnicodeError):
            raise MutationConflict('Arquivo indisponível. Avise a administração.',409)
        service.audit(db,row,identity.id,'ler_arquivo' if leitor.modo_leitura() else 'baixar_arquivo')
        db.commit()
        extension = {'application/pdf':'.pdf','image/png':'.png','image/jpeg':'.jpg'}[row.mime]
        response = send_file(io.BytesIO(content),mimetype=row.mime,as_attachment=True,
            download_name=(secure_filename(row.titulo) or 'material')+extension)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response


def section_result(body, status, pair_id):
    if wants_json():
        return jsonify(body),status
    flash(body['mensagem'],'success')
    return redirect(url_for('estudos.abas',pair_id=pair_id))


@estudo_bp.route('/estudos/disciplinas/<int:pair_id>/abas',methods=['GET','POST'])
def abas(pair_id):
    identity = g.estudo_identity
    if identity.papel == 'aluno':
        raise MutationConflict('Somente docentes e administração organizam abas.',403)
    with get_session() as db:
        pair,classroom,subject = service.pair_access(db,identity,pair_id)
        if not service.sections_enabled(db):
            raise MutationConflict('A organização das abas ainda não foi habilitada nesta instalação.',503)
        if request.method == 'GET':
            return render_template('estudo_abas.html',pair=pair,turma=classroom,disciplina=subject,
                sections=service.sections(db,pair.id,archived=True),identity=identity)
        payload = data()
        entry,replay = begin_submission(db,f'estudo:aba:criar:{pair.id}',identity.id)
        if replay:
            return section_result(*replay,pair.id)
        values = service.section_fields(payload)
        row = SecaoEstudoModel(turma_disciplina_id=pair.id,autor_id=identity.id,**values)
        db.add(row)
        db.flush()
        service.section_audit(db,row,identity.id,'criar')
        return section_result(*finish_submission(db,entry,{'id':row.id,'versao':row.versao,
            'mensagem':'Aba criada. A publicação dos conteúdos continua sujeita à revisão.'},201),pair.id)


@estudo_bp.post('/estudos/abas/<int:section_id>/<action>')
def alterar_aba(section_id,action):
    if action not in {'editar','arquivar'}:
        raise MutationConflict('Ação não encontrada.',404)
    identity,payload = g.estudo_identity,data()
    with get_session() as db:
        row = service.section_access(db,identity,section_id,edit=True)
        entry,replay = begin_submission(db,f'estudo:aba:{action}:{row.id}',identity.id)
        if replay:
            return section_result(*replay,row.turma_disciplina_id)
        if row.estado != 'ativa':
            raise MutationConflict('Esta aba foi arquivada. Seu conteúdo e histórico foram preservados.')
        values = service.section_fields(payload) if action == 'editar' else {}
        check_version(row,payload)
        if action == 'editar':
            row.nome,row.ordem = values['nome'],values['ordem']
        else:
            row.estado = 'arquivada'
        service.section_audit(db,row,identity.id,action)
        return section_result(*finish_submission(db,entry,{'id':row.id,'versao':row.versao,
            'estado':row.estado,'mensagem':'Aba atualizada.' if action=='editar' else
            'Aba arquivada. Os alunos perderam o acesso aos conteúdos desta aba; o histórico foi preservado.'},200),row.turma_disciplina_id)
