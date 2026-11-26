"""Opt-in fixtures for the isolated manual environment, never production seeds."""
import os

from werkzeug.security import generate_password_hash
from app.database import engine, get_session
from app.models import (AlunoModel, AlunoDisciplinaModel, AlunoTurmaModel,
    DisciplinaModel, ProfessorModel, ProfessorDisciplinaModel, ProfessorTurmaModel,
    TurmaDisciplinaModel, TurmaModel, UsuarioModel)
from config import Config

TEST_PASSWORD = 'Teste-local-2026!'
ACCOUNTS = {'superadmin@teste.local': 'super_admin', 'admin@teste.local': 'admin',
            'professor@teste.local': 'professor', 'aluno@teste.local': 'aluno'}


def _get_or_add(db, model, match, **values):
    row = db.query(model).filter_by(**match).first()
    if row is None:
        row = model(**match, **values)
        db.add(row)
        db.flush()
    return row


def populate(db):
    """Add missing fictitious records; never reset accounts, roles or passwords."""
    users = {}
    for email, role in ACCOUNTS.items():
        user = db.query(UsuarioModel).filter_by(email=email).first()
        if user is not None and user.tipo != role:
            raise RuntimeError('Conta de teste existente com papel diferente; nada foi alterado.')
        if user is None:
            user = UsuarioModel(email=email, tipo=role, estado='ativo',
                                senha=generate_password_hash(TEST_PASSWORD))
            db.add(user)
            db.flush()
        users[role] = user
    teacher = _get_or_add(db, ProfessorModel, {'usuario_id': users['professor'].id},
        nome='Professor de Teste', cpf='00000000000', disciplina_principal='Matematica de Teste')
    student = _get_or_add(db, AlunoModel, {'usuario_id': users['aluno'].id},
        nome='Aluno de Teste', cpf='00000000000', matricula='TESTE-2026-001',
        curso_serie='1 ano - teste', status_matricula='Ativo')
    classroom = _get_or_add(db, TurmaModel, {'codigo': 'TESTE-2026'},
        nome='Turma de Teste', ano_letivo=2026, turno='Matutino')
    subject = _get_or_add(db, DisciplinaModel, {'codigo': 'MAT-TESTE'},
        nome='Matematica de Teste', carga_horaria=60)
    for model, match in [
        (ProfessorTurmaModel, {'professor_id': teacher.id, 'turma_id': classroom.id}),
        (ProfessorDisciplinaModel, {'professor_id': teacher.id, 'disciplina_id': subject.id}),
        (AlunoTurmaModel, {'aluno_id': student.id, 'turma_id': classroom.id}),
        (AlunoDisciplinaModel, {'aluno_id': student.id, 'disciplina_id': subject.id}),
        (TurmaDisciplinaModel, {'turma_id': classroom.id, 'disciplina_id': subject.id}),
    ]:
        _get_or_add(db, model, match)


def main():
    if (os.getenv('EDUFAST_MANUAL_TEST') != '1' or Config.APP_ENV != 'development'
            or engine.url.get_backend_name() != 'postgresql' or engine.url.host != 'db'
            or engine.url.database != 'edufast_manual'):
        raise RuntimeError('Fixtures permitidas somente no banco isolado edufast_manual do iniciador local.')
    with get_session() as db:
        populate(db)
        db.commit()
    print('Contas e vinculos de teste preparados. Senhas, estados e permissoes existentes preservados.')


if __name__ == '__main__':
    main()
