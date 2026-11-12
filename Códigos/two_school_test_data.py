"""Dados fictícios exclusivamente para os dois bancos locais de demonstração."""
import json
import os
import sys

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from app.database import Base, engine
from app import models
from app.models import (AlunoModel, AlunoDisciplinaModel, AlunoTurmaModel,
    DisciplinaModel, ProfessorModel, ProfessorDisciplinaModel, ProfessorTurmaModel,
    TurmaDisciplinaModel, TurmaModel, UsuarioModel)
from app.models.escola_model import IdentidadeEscolaModel
from config import Config

FIXTURE = 'duas-escolas-v1'
PASSWORD = 'Teste-escolas-2026!'
SUBJECTS = [('MAT', 'Matemática'), ('POR', 'Português'), ('CIE', 'Ciências')]


def validate_target(config, url, environment):
    school = environment.get('EDUFAST_TEST_SCHOOL')
    if (environment.get('EDUFAST_TWO_SCHOOLS_TEST') != '1'
            or school not in {'teste01', 'teste02'}
            or config.APP_ENV != 'development' or config.DB_URL
            or url.get_backend_name() != 'mysql'
            or url.host != f'db-{school}' or url.database != f'edufast_{school}'):
        raise RuntimeError('Permitido somente nos bancos MySQL locais isolados teste01/teste02.')
    return school


def summary(db, school):
    return {'escola': school, 'alunos': db.query(AlunoModel).count(),
            'professores': db.query(ProfessorModel).count(),
            'materias': db.query(DisciplinaModel).count(),
            'turmas': db.query(TurmaModel).count(),
            'matriculas': db.query(AlunoTurmaModel).count(),
            'alunos_materias': db.query(AlunoDisciplinaModel).count(),
            'professores_materias': db.query(ProfessorDisciplinaModel).count()}


def verify(db, school):
    identity = db.get(IdentidadeEscolaModel, 1)
    if not identity or json.loads(identity.dados).get('fixture') != f'{FIXTURE}:{school}':
        raise RuntimeError('Banco sem identificação desta demonstração; nada alterado.')
    result = summary(db, school)
    expected = {'alunos': 20, 'professores': 5, 'materias': 3, 'turmas': 1,
                'matriculas': 20, 'alunos_materias': 60, 'professores_materias': 5}
    if any(result[key] != value for key, value in expected.items()):
        raise RuntimeError('Quantidades diferentes do cenário; dados existentes preservados.')
    return result


def initialize(target_engine, school):
    """Cria esquema somente em banco vazio; nunca migra ou limpa tabelas existentes."""
    if school not in {'teste01', 'teste02'}:
        raise RuntimeError('Escola de teste inválida.')
    tables = inspect(target_engine).get_table_names()
    if tables:
        # Reconhecer módulo instalado por migration revisada, sem criar suas tabelas.
        frequency_tables = {'frequencia_chamadas', 'frequencia_presencas', 'frequencia_atestados', 'frequencia_auditoria'}
        if frequency_tables <= set(tables):
            from app.models import frequencia_model  # noqa: F401
        if set(tables) != set(Base.metadata.tables):
            raise RuntimeError('Esquema existente diferente; revisão necessária, sem alteração.')
        with Session(target_engine) as db:
            # Um esquema vazio de uma tentativa interrompida pode receber a fixture.
            has_rows = any(db.execute(select(table).limit(1)).first() is not None
                           for table in Base.metadata.sorted_tables)
            if has_rows:
                return verify(db, school)
    else:
        Base.metadata.create_all(target_engine)
    number = school[-2:]
    with Session(target_engine) as db, db.begin():
        db.add(IdentidadeEscolaModel(id=1, versao=1, dados=json.dumps({
            'nome': f'Escola Teste {number}', 'sigla': f'T{number}',
            'subtitulo': 'AMBIENTE DE TESTE', 'fixture': f'{FIXTURE}:{school}'}, ensure_ascii=False)))
        def user(email, role):
            row = UsuarioModel(email=f'{email}@{school}.local', tipo=role, estado='ativo',
                               senha=generate_password_hash(PASSWORD))
            db.add(row)
            db.flush()
            return row
        user('admin', 'admin')
        classroom = TurmaModel(nome=f'Turma Teste {number}', codigo='TURMA-2026',
                               ano_letivo=2026, turno='Matutino')
        db.add(classroom)
        subjects = [DisciplinaModel(codigo=code, nome=name, carga_horaria=60)
                    for code, name in SUBJECTS]
        db.add_all(subjects)
        db.flush()
        for subject in subjects:
            db.add(TurmaDisciplinaModel(turma_id=classroom.id, disciplina_id=subject.id))
        for i in range(1, 6):
            account = user(f'professor{i:02}', 'professor')
            subject = subjects[(i - 1) % 3]
            # Identificadores fictícios deliberadamente não válidos para uso cadastral real.
            teacher = ProfessorModel(usuario_id=account.id, nome=f'Professor {i:02} - Teste {number}',
                cpf=f'TESTE{number}P{i:02}', disciplina_principal=subject.nome)
            db.add(teacher)
            db.flush()
            db.add(ProfessorTurmaModel(professor_id=teacher.id, turma_id=classroom.id))
            db.add(ProfessorDisciplinaModel(professor_id=teacher.id, disciplina_id=subject.id))
        for i in range(1, 21):
            account = user(f'aluno{i:02}', 'aluno')
            student = AlunoModel(usuario_id=account.id, nome=f'Aluno {i:02} - Teste {number}',
                matricula=f'TESTE-{i:03}', curso_serie='Turma de demonstração', status_matricula='Ativo')
            db.add(student)
            db.flush()
            db.add(AlunoTurmaModel(aluno_id=student.id, turma_id=classroom.id))
            for subject in subjects:
                db.add(AlunoDisciplinaModel(aluno_id=student.id, disciplina_id=subject.id))
        db.flush()
        return verify(db, school)


def main():
    school = validate_target(Config, engine.url, os.environ)
    if sys.argv[1:] == ['--verify']:
        with Session(engine) as db:
            result = verify(db, school)
    elif not sys.argv[1:]:
        result = initialize(engine, school)
    else:
        raise RuntimeError('Use sem argumentos ou --verify.')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
