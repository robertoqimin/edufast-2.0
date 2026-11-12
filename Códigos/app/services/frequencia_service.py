"""Chamada docente pendente, decisão administrativa e faltas justificadas."""
from datetime import date
from decimal import Decimal
from app.concurrency import MutationConflict, check_version
from app.models import (AlunoModel, AlunoTurmaModel, ProfessorModel, ProfessorTurmaModel,
                        ProfessorDisciplinaModel, TurmaDisciplinaModel, TurmaModel, DisciplinaModel, UsuarioModel)
from app.models.curso_model import AtribuicaoDocenteModel, EstadoTurmaModel
from app.models.frequencia_model import ChamadaModel, PresencaModel, AtestadoModel, AuditoriaFrequenciaModel


def integer(value):
    raw = str(value)
    if isinstance(value, bool) or not raw.isascii() or not raw.isdecimal() or len(raw) > 10 or not 1 <= int(raw) <= 2147483647:
        raise MutationConflict('Identificador inválido.', 400)
    return int(value)


def day(value):
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise MutationConflict('Data inválida.', 400)


def audit(db, actor, action, resource):
    db.add(AuditoriaFrequenciaModel(ator_id=actor, acao=action, referencia=resource))


def scope(db, identity, pair_id):
    pair = db.get(TurmaDisciplinaModel, integer(pair_id))
    if not pair:
        raise MutationConflict('Turma/disciplina não encontrada.', 404)
    if identity.admin:
        return pair
    if identity.papel != 'professor':
        raise MutationConflict('Acesso não autorizado.', 403)
    teacher = db.query(ProfessorModel).filter_by(usuario_id=identity.id).first()
    if not teacher:
        raise MutationConflict('Professor sem vínculo.', 403)
    # Atribuição explícita tem prioridade; legado só quando a oferta não foi reconciliada.
    assignments = db.query(AtribuicaoDocenteModel).filter_by(turma_disciplina_id=pair.id).all()
    if assignments:
        allowed = any(a.professor_id == teacher.id and a.ativo for a in assignments)
    else:
        allowed = (db.query(ProfessorTurmaModel.id).filter_by(professor_id=teacher.id, turma_id=pair.turma_id).first()
                   and db.query(ProfessorDisciplinaModel.id).filter_by(professor_id=teacher.id, disciplina_id=pair.disciplina_id).first())
    if not allowed:
        raise MutationConflict('Turma/disciplina fora dos vínculos do professor.', 403)
    return pair


def students(db, pair):
    return db.query(AlunoModel).join(AlunoTurmaModel, AlunoTurmaModel.aluno_id == AlunoModel.id).filter(
        AlunoTurmaModel.turma_id == pair.turma_id).order_by(AlunoModel.nome, AlunoModel.id).all()


def student_access(db, identity, student_id):
    student = db.get(AlunoModel, integer(student_id))
    if not student or (not identity.admin and (identity.papel != 'aluno' or student.usuario_id != identity.id)):
        raise MutationConflict('Aluno não encontrado no acesso autorizado.', 404)
    return student


def propose(db, identity, data):
    if identity.papel != 'professor':
        raise MutationConflict('Somente o professor envia a chamada.', 403)
    pair = scope(db, identity, data.get('turma_disciplina_id'))
    # Serializa as revisões da oferta inclusive quando ainda não existe chamada.
    db.query(TurmaDisciplinaModel).filter_by(id=pair.id).with_for_update().one()
    archived = db.get(EstadoTurmaModel, pair.turma_id)
    if archived and archived.arquivada:
        raise MutationConflict('Turma arquivada.', 409)
    when, lesson = day(data.get('dia')), integer(data.get('aula'))
    if when > date.today() or lesson > 20:
        raise MutationConflict('Confira a data e o número da aula (1 a 20).', 400)
    previous = db.query(ChamadaModel).filter_by(turma_disciplina_id=pair.id, dia=when, aula=lesson).order_by(
        ChamadaModel.revisao.desc()).with_for_update().all()
    if any(c.estado == 'pendente' for c in previous):
        raise MutationConflict('Já existe chamada pendente para essa aula.')
    approved = next((c for c in previous if c.estado == 'aprovada'), None)
    reason = str(data.get('motivo') or '').strip()
    if len(reason) > 500 or (approved and len(reason) < 5):
        raise MutationConflict('Informe um motivo de correção entre 5 e 500 caracteres.', 400)
    roster = ({p.aluno_id for p in db.query(PresencaModel).filter_by(chamada_id=approved.id)}
              if approved else {s.id for s in students(db, pair)})
    raw = data.get('presencas')
    if not roster or not isinstance(raw, dict):
        raise MutationConflict('Informe a situação de todos os alunos da chamada.', 400)
    try:
        marks = {integer(k): v for k, v in raw.items()}
    except (ValueError, TypeError):
        raise MutationConflict('Lista de alunos inválida.', 400)
    if len(marks) != len(raw) or set(marks) != roster or any(v not in ('presente', 'falta') for v in marks.values()):
        raise MutationConflict('A chamada deve conter exatamente os alunos da turma e situações válidas.', 400)
    call = ChamadaModel(turma_disciplina_id=pair.id, dia=when, aula=lesson,
        revisao=(previous[0].revisao + 1 if previous else 1), anterior_id=approved.id if approved else None,
        autor_id=identity.id, estado='pendente', motivo=reason)
    db.add(call)
    db.flush()
    db.add_all(PresencaModel(chamada_id=call.id, aluno_id=sid, situacao=status) for sid, status in marks.items())
    audit(db, identity.id, 'propor_chamada', call.id)
    return call


def decide(db, identity, kind, resource_id, data):
    if not identity.admin:
        raise MutationConflict('Somente a administração decide.', 403)
    model = ChamadaModel if kind == 'chamada' else AtestadoModel
    row = db.query(model).filter_by(id=integer(resource_id)).with_for_update().first()
    if not row:
        raise MutationConflict('Registro não encontrado.', 404)
    if row.estado != 'pendente':
        raise MutationConflict('Registro já decidido.')
    check_version(row, data)
    decision = data.get('decisao')
    reason = str(data.get('motivo') or '').strip()
    if decision not in ('aprovar', 'rejeitar') or not 5 <= len(reason) <= 500:
        raise MutationConflict('Informe decisão e motivo (5 a 500 caracteres).', 400)
    if kind == 'chamada' and decision == 'aprovar':
        from app.services.identidade_service import Identidade
        author = db.get(UsuarioModel, row.autor_id)
        if not author or author.estado != 'ativo' or author.tipo != 'professor':
            raise MutationConflict('Autor sem acesso docente ativo.', 403)
        pair = scope(db, Identidade(author.id, author.tipo, False, author.auth_version), row.turma_disciplina_id)
        archived = db.get(EstadoTurmaModel, pair.turma_id)
        if archived and archived.arquivada:
            raise MutationConflict('Turma arquivada; chamada não pode ser publicada.')
        if row.anterior_id:
            old = db.query(ChamadaModel).filter_by(id=row.anterior_id).with_for_update().one()
            if old.estado != 'aprovada':
                raise MutationConflict('A chamada anterior foi alterada; revise a correção.')
            old.estado = 'substituida'
    row.estado = ('aprovada' if kind == 'chamada' else 'aceito') if decision == 'aprovar' else 'rejeitado' if kind == 'atestado' else 'rejeitada'
    row.decidido_por = identity.id
    if kind == 'chamada':
        row.decisao_motivo = reason
    else:
        row.motivo = reason
    audit(db, identity.id, f'{decision}_{kind}', row.id)
    return row


def submit_certificate(db, identity, data, filename, mime):
    student = student_access(db, identity, data.get('aluno_id'))
    start, end = day(data.get('inicio')), day(data.get('fim'))
    if end < start or (end - start).days > 366:
        raise MutationConflict('Confira o período do atestado (até 367 dias).', 400)
    row = AtestadoModel(aluno_id=student.id, inicio=start, fim=end, arquivo=filename, mime=mime,
                        enviado_por=identity.id, estado='pendente')
    db.add(row)
    db.flush()
    audit(db, identity.id, 'enviar_atestado', row.id)
    return row


def report(db, identity, start, end, pair_id=None, student_id=None):
    if end < start or (end - start).days > 366:
        raise MutationConflict('Selecione um intervalo de até 367 dias.', 400)
    query = db.query(ChamadaModel, PresencaModel, AlunoModel, TurmaModel.nome, DisciplinaModel.nome).join(PresencaModel,
        PresencaModel.chamada_id == ChamadaModel.id).join(AlunoModel, AlunoModel.id == PresencaModel.aluno_id).join(
        TurmaDisciplinaModel, TurmaDisciplinaModel.id == ChamadaModel.turma_disciplina_id).join(
        TurmaModel, TurmaModel.id == TurmaDisciplinaModel.turma_id).join(
        DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id).filter(
        ChamadaModel.estado == 'aprovada', ChamadaModel.dia >= start, ChamadaModel.dia <= end)
    if pair_id:
        scope(db, identity, pair_id)
        query = query.filter(ChamadaModel.turma_disciplina_id == integer(pair_id))
    elif not identity.admin and identity.papel != 'aluno':
        raise MutationConflict('Selecione uma turma/disciplina autorizada.', 400)
    if identity.papel == 'aluno':
        query = query.filter(AlunoModel.usuario_id == identity.id)
    elif student_id:
        query = query.filter(AlunoModel.id == integer(student_id))
    certificates = db.query(AtestadoModel.aluno_id, AtestadoModel.inicio, AtestadoModel.fim).filter(
        AtestadoModel.estado == 'aceito', AtestadoModel.inicio <= end, AtestadoModel.fim >= start)
    if identity.papel == 'aluno':
        certificates = certificates.join(AlunoModel, AlunoModel.id == AtestadoModel.aluno_id).filter(AlunoModel.usuario_id == identity.id)
    valid = {}
    for sid, first, last in certificates:
        valid.setdefault(sid, []).append((first, last))
    totals, details = {}, []
    for call, mark, student, classroom, subject in query.order_by(ChamadaModel.dia, AlunoModel.nome, ChamadaModel.aula):
        justified = mark.situacao == 'falta' and any(a <= call.dia <= b for a, b in valid.get(student.id, []))
        status = 'justificada' if justified else mark.situacao
        item = totals.setdefault(student.id, {'aluno_id': student.id, 'nome': student.nome, 'presentes': 0, 'faltas': 0, 'justificadas': 0})
        item[{'presente': 'presentes', 'falta': 'faltas', 'justificada': 'justificadas'}[status]] += 1
        details.append({'dia': call.dia.isoformat(), 'aula': call.aula, 'aluno_id': student.id,
            'nome': student.nome, 'turma_disciplina_id': call.turma_disciplina_id,
            'turma': classroom, 'materia': subject, 'situacao': status})
    for item in totals.values():
        total = item['presentes'] + item['faltas'] + item['justificadas']
        item['total'] = total
        item['faltas_total'] = item['faltas'] + item['justificadas']
        item['percentual_presenca'] = str((Decimal(item['presentes']) * 100 / total).quantize(Decimal('.01')))
    return {'totais': list(totals.values()), 'registros': details}
