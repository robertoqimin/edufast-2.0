import csv
import hmac
import io
from datetime import date
from pathlib import Path
from uuid import uuid4
from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, send_file, session, url_for, flash
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from app.database import engine, get_session
from app.concurrency import MutationConflict, begin_submission, finish_submission
from app.services.identidade_service import require_role

frequencia_bp = Blueprint('frequencia', __name__)
TABLES = {'frequencia_chamadas', 'frequencia_presencas', 'frequencia_atestados', 'frequencia_auditoria'}


def is_json():
    return request.is_json or request.args.get('formato') == 'json'


@frequencia_bp.before_request
def boundary():
    g.frequencia_identity = require_role('admin', 'super_admin', 'professor', 'aluno')
    if request.method == 'POST' and not request.headers.get('Authorization'):
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
        if not token or not hmac.compare_digest(str(session.get('csrf_token', '')), token):
            raise MutationConflict('Recarregue o formulário para confirmar seu envio.', 403)
    if not TABLES <= set(inspect(engine).get_table_names()):
        if is_json():
            return jsonify(erro='Frequência ainda não habilitada nesta instalação.'), 503
        return render_template('frequencia_erro.html', mensagem='A frequência ainda não foi habilitada pela administração. Os dados atuais estão preservados.'), 503


@frequencia_bp.errorhandler(MutationConflict)
def conflict(error):
    if is_json():
        return jsonify(erro=error.message), error.status
    return render_template('frequencia_erro.html', mensagem=error.message), error.status


@frequencia_bp.errorhandler(IntegrityError)
def integrity(error):
    return conflict(MutationConflict('Outro envio alterou esta chamada. Recarregue antes de tentar novamente.'))


def result(body, status=200):
    if is_json():
        return jsonify(body), status
    flash(body.get('mensagem', 'Envio registrado.'), 'success')
    return redirect(url_for('frequencia.painel'))


@frequencia_bp.get('/frequencia')
def painel():
    from app.services import frequencia_service as service
    from app.models import AlunoModel, TurmaDisciplinaModel, TurmaModel, DisciplinaModel
    from app.models.frequencia_model import ChamadaModel, AtestadoModel
    identity = g.frequencia_identity
    with get_session() as db:
        pairs = []
        if identity.papel != 'aluno':
            for pair, turma, subject in db.query(TurmaDisciplinaModel, TurmaModel, DisciplinaModel).join(
                    TurmaModel, TurmaModel.id == TurmaDisciplinaModel.turma_id).join(
                    DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id).order_by(TurmaModel.nome, DisciplinaModel.nome):
                try:
                    service.scope(db, identity, pair.id)
                    pairs.append({'id': pair.id, 'nome': f'{turma.nome} · {subject.nome}'})
                except MutationConflict as exc:
                    if exc.status != 403:
                        raise
        calls = db.query(ChamadaModel).order_by(ChamadaModel.criada_em.desc(), ChamadaModel.id.desc())
        if not identity.admin:
            calls = calls.filter(ChamadaModel.autor_id == identity.id)
        certificates = db.query(AtestadoModel).order_by(AtestadoModel.id.desc())
        pupils = db.query(AlunoModel).order_by(AlunoModel.nome)
        if not identity.admin:
            pupils = pupils.filter(AlunoModel.usuario_id == identity.id)
            certificates = certificates.join(AlunoModel, AlunoModel.id == AtestadoModel.aluno_id).filter(AlunoModel.usuario_id == identity.id)
        pupil_list = pupils.all() if identity.admin or identity.papel == 'aluno' else []
        return render_template('frequencia_painel.html', pairs=pairs, pair_names={p['id']:p['nome'] for p in pairs}, calls=calls.limit(100).all(),
            certificates=certificates.limit(100).all() if identity.admin or identity.papel == 'aluno' else [],
            pupils=pupil_list, student_names={s.id:s.nome for s in pupil_list}, identity=identity, today=date.today().isoformat())


@frequencia_bp.get('/frequencia/turmas/<int:pair_id>/chamada')
def formulario(pair_id):
    from app.services import frequencia_service as service
    from app.models import TurmaModel, DisciplinaModel
    from app.models.frequencia_model import ChamadaModel, PresencaModel
    from app.models.curso_model import EstadoTurmaModel
    identity = g.frequencia_identity
    if identity.papel != 'professor':
        raise MutationConflict('Somente o professor envia chamada.', 403)
    with get_session() as db:
        pair = service.scope(db, identity, pair_id)
        archived = db.get(EstadoTurmaModel, pair.turma_id)
        if archived and archived.arquivada:
            raise MutationConflict('Turma arquivada.', 409)
        previous, marks = None, {}
        pupils = service.students(db, pair)
        if request.args.get('chamada_id'):
            previous = db.get(ChamadaModel, service.integer(request.args['chamada_id']))
            if not previous or previous.turma_disciplina_id != pair.id:
                raise MutationConflict('Chamada não encontrada.', 404)
            if previous.estado != 'aprovada':
                raise MutationConflict('Abra uma chamada confirmada e vigente para corrigir.', 409)
            from app.models import AlunoModel
            rows = db.query(PresencaModel, AlunoModel).join(AlunoModel,
                AlunoModel.id == PresencaModel.aluno_id).filter(
                PresencaModel.chamada_id == previous.id).order_by(AlunoModel.nome, AlunoModel.id).all()
            pupils = [student for mark, student in rows]
            marks = {mark.aluno_id: mark.situacao for mark, student in rows}
        return render_template('frequencia_chamada.html', pair=pair, alunos=pupils, anterior=previous, marcacoes=marks,
            turma=db.get(TurmaModel, pair.turma_id), disciplina=db.get(DisciplinaModel, pair.disciplina_id), today=date.today().isoformat())


@frequencia_bp.post('/frequencia/chamadas')
def propor():
    from app.services import frequencia_service as service
    data = request.get_json() if request.is_json else request.form.to_dict()
    if not request.is_json:
        data['presencas'] = {k.removeprefix('aluno_'): v for k, v in request.form.items() if k.startswith('aluno_')}
    if not isinstance(data, dict):
        raise MutationConflict('Corpo inválido.', 400)
    with get_session() as db:
        entry, replay = begin_submission(db, 'frequencia:chamada', g.frequencia_identity.id)
        if replay:
            return result(*replay)
        call = service.propose(db, g.frequencia_identity, data)
        return result(*finish_submission(db, entry, {'id': call.id, 'estado': call.estado, 'versao': call.versao,
            'mensagem': 'Correção confirmada. O histórico anterior foi preservado.' if call.anterior_id
                else 'Chamada confirmada. A frequência já está disponível no relatório.'}, 201))


@frequencia_bp.get('/frequencia/chamadas/<int:call_id>')
def chamada(call_id):
    from app.services import frequencia_service as service
    from app.models import AlunoModel, TurmaModel, DisciplinaModel
    from app.models.frequencia_model import ChamadaModel, PresencaModel
    with get_session() as db:
        call = db.get(ChamadaModel, call_id)
        if not call:
            raise MutationConflict('Chamada não encontrada.', 404)
        pair = service.scope(db, g.frequencia_identity, call.turma_disciplina_id)
        marks = db.query(PresencaModel, AlunoModel).join(AlunoModel, AlunoModel.id == PresencaModel.aluno_id).filter(
            PresencaModel.chamada_id == call.id).order_by(AlunoModel.nome).all()
        if is_json():
            return jsonify(id=call.id, estado=call.estado, versao=call.versao,
                alunos=[{'id': s.id, 'nome': s.nome, 'situacao': mark.situacao} for mark, s in marks])
        return render_template('frequencia_detalhe.html', call=call, marks=marks, identity=g.frequencia_identity,
            turma=db.get(TurmaModel, pair.turma_id), disciplina=db.get(DisciplinaModel, pair.disciplina_id))


@frequencia_bp.post('/frequencia/<kind>/<int:resource_id>/decidir')
def decidir(kind, resource_id):
    from app.services import frequencia_service as service
    if kind not in ('chamada', 'atestado'):
        raise MutationConflict('Operação inválida.', 404)
    data = request.get_json() if request.is_json else request.form
    if not isinstance(data, dict) and not hasattr(data, 'get'):
        raise MutationConflict('Corpo inválido.', 400)
    with get_session() as db:
        entry, replay = begin_submission(db, f'frequencia:decidir:{kind}:{resource_id}', g.frequencia_identity.id)
        if replay:
            return result(*replay)
        row = service.decide(db, g.frequencia_identity, kind, resource_id, data)
        return result(*finish_submission(db, entry, {'id': row.id, 'estado': row.estado, 'mensagem': 'Decisão registrada.'}, 200))


@frequencia_bp.post('/frequencia/atestados')
def enviar_atestado():
    from app.services import frequencia_service as service
    from app.crypto import cipher, FILE_PREFIX
    upload = request.files.get('arquivo')
    if not upload:
        raise MutationConflict('Anexe um PDF, PNG ou JPEG de até 5 MiB.', 400)
    content = upload.stream.read(5 * 1024 * 1024 + 1)
    upload.stream.seek(0)
    mime = ('application/pdf' if content.startswith(b'%PDF-') else 'image/png' if content.startswith(b'\x89PNG\r\n\x1a\n')
            else 'image/jpeg' if content.startswith(b'\xff\xd8\xff') else None)
    if not mime or len(content) > 5 * 1024 * 1024:
        raise MutationConflict('Arquivo inválido ou maior que 5 MiB. Use PDF, PNG ou JPEG.', 400)
    target = None
    try:
        with get_session() as db:
            entry, replay = begin_submission(db, 'frequencia:atestado', g.frequencia_identity.id)
            if replay:
                return result(*replay)
            name = uuid4().hex + '.enc'
            row = service.submit_certificate(db, g.frequencia_identity, request.form, name, mime)
            folder = Path(current_app.config['UPLOAD_FOLDER']) / 'frequencia'
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            target = folder / name
            with target.open('xb') as file:
                file.write(FILE_PREFIX + cipher().encrypt(content))
            target.chmod(0o600)
            response = finish_submission(db, entry, {'id': row.id, 'estado': 'pendente',
                'mensagem': 'Atestado enviado para análise. A falta só será justificada após aceite.'}, 201)
            target = None
            return result(*response)
    finally:
        if target and target.exists():
            target.unlink()


@frequencia_bp.get('/frequencia/atestados/<int:resource_id>/arquivo')
def arquivo(resource_id):
    from app.services import frequencia_service as service
    from app.crypto import cipher, FILE_PREFIX
    from app.models.frequencia_model import AtestadoModel
    with get_session() as db:
        row = db.get(AtestadoModel, resource_id)
        if not row:
            raise MutationConflict('Atestado não encontrado.', 404)
        service.student_access(db, g.frequencia_identity, row.aluno_id)
        # Nome sempre gerado pelo servidor; nunca aceitar caminho do navegador.
        if len(row.arquivo) != 36 or not row.arquivo.endswith('.enc') or any(c not in '0123456789abcdef' for c in row.arquivo[:-4]):
            raise MutationConflict('Arquivo indisponível.', 404)
        source = Path(current_app.config['UPLOAD_FOLDER']) / 'frequencia' / row.arquivo
        if not source.is_file():
            raise MutationConflict('Arquivo indisponível.', 404)
        encoded = source.read_bytes()
        if not encoded.startswith(FILE_PREFIX):
            raise MutationConflict('Arquivo indisponível.', 409)
        content = cipher().decrypt(encoded[len(FILE_PREFIX):])
        service.audit(db, g.frequencia_identity.id, 'baixar_atestado', row.id)
        db.commit()
        extension = {'application/pdf': 'pdf', 'image/png': 'png', 'image/jpeg': 'jpg'}[row.mime]
        response = send_file(io.BytesIO(content), mimetype=row.mime, as_attachment=True, download_name=f'atestado-{row.id}.{extension}')
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response


@frequencia_bp.get('/frequencia/relatorio')
def relatorio():
    from app.services import frequencia_service as service
    identity = g.frequencia_identity
    if request.args.get('formato') == 'csv' and not identity.admin:
        raise MutationConflict('Somente a administração exporta o relatório.', 403)
    start = service.day(request.args.get('inicio', date.today().replace(day=1).isoformat()))
    end = service.day(request.args.get('fim', date.today().isoformat()))
    pair_id, student_id = request.args.get('turma_disciplina_id'), request.args.get('aluno_id')
    with get_session() as db:
        report = service.report(db, identity, start, end, pair_id, student_id)
        if request.args.get('formato') == 'csv':
            service.audit(db, identity.id, 'exportar_relatorio', 0)
            db.commit()
    if request.args.get('formato') == 'csv':
        out = io.StringIO()
        writer = csv.writer(out, delimiter=';')
        writer.writerow(['Período', start.isoformat(), end.isoformat()])
        writer.writerow(['Aluno', 'Nome', 'Aulas', 'Presenças', 'Faltas não justificadas', 'Faltas justificadas', 'Faltas totais', 'Presença %'])
        for row in report['totais']:
            name = row['nome']
            if name.lstrip().startswith(('=', '+', '-', '@')) or name.startswith(('\t', '\r', '\n')):
                name = "'" + name
            writer.writerow([row['aluno_id'], name, row['total'], row['presentes'], row['faltas'], row['justificadas'], row['faltas_total'], row['percentual_presenca']])
        return out.getvalue(), 200, {'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': 'attachment; filename="frequencia.csv"', 'Cache-Control': 'no-store'}
    if is_json():
        return jsonify(report), 200, {'Cache-Control': 'no-store'}
    return render_template('frequencia_relatorio.html', report=report, start=start, end=end, identity=identity)
