from datetime import date

from flask import abort
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.services.arquivos_service import _remove_saved_file, _save_profile_photo
from app.database import get_session
from app.concurrency import check_version, insert_if_missing, begin_submission, finish_submission
from app.models import (
    AlunoModel,
    AlunoTurmaModel,
    ComunicadoModel,
    DisciplinaModel,
    DocumentoModel,
    NotaModel,
    ProfessorDisciplinaModel,
    ProfessorModel,
    ProfessorTurmaModel,
    SolicitacaoDocumentoModel,
    TurmaDisciplinaModel,
    TurmaModel,
    UsuarioModel,
)


def get_disciplinas(*, session_factory=get_session):
    from app.repositories.academico_repository import load_get_disciplinas
    from app.presenters.admin_presenter import present_get_disciplinas
    db = session_factory()
    try:
        values = load_get_disciplinas(db)
        return present_get_disciplinas(**values)
    except LookupError:
        abort(404)
    finally:
        db.close()


def get_disciplinas_page_data(*, session_factory=get_session):
    from app.repositories.academico_repository import load_get_disciplinas_page_data
    from app.presenters.admin_presenter import present_get_disciplinas_page_data
    db = session_factory()
    try:
        values = load_get_disciplinas_page_data(db)
        return present_get_disciplinas_page_data(**values)
    except LookupError:
        abort(404)
    finally:
        db.close()


def get_turmas_page_data(*, session_factory=get_session):
    from app.repositories.academico_repository import load_get_turmas_page_data
    from app.presenters.admin_presenter import present_get_turmas_page_data
    db = session_factory()
    try:
        values = load_get_turmas_page_data(db)
        return present_get_turmas_page_data(**values)
    except LookupError:
        abort(404)
    finally:
        db.close()


def criar_disciplina(data, *, session_factory=get_session):
    nome = (data.get("nome") or "").strip()
    codigo = (data.get("codigo") or "").strip().upper()
    carga_horaria_raw = (data.get("carga_horaria") or "").strip()

    if not nome or not codigo or not carga_horaria_raw:
        return {"erro": "Nome, codigo e carga horaria sao obrigatorios"}, 400

    try:
        carga_horaria = int(carga_horaria_raw)
    except ValueError:
        return {"erro": "Carga horaria deve ser um numero inteiro"}, 400

    if carga_horaria < 0:
        return {"erro": "Carga horaria nao pode ser negativa"}, 400

    db = session_factory()
    try:
        disciplina = DisciplinaModel(
            nome=nome[:120],
            codigo=codigo[:30],
            carga_horaria=carga_horaria,
        )
        db.add(disciplina)
        db.commit()
        return {"id": disciplina.id}, 201
    except IntegrityError:
        db.rollback()
        return {"erro": "Codigo de disciplina ja cadastrado"}, 409
    finally:
        db.close()

def associar_professor_disciplina(data, *, session_factory=get_session):
    professor_id = data.get("professor_id", type=int)
    disciplina_id = data.get("disciplina_id", type=int)

    if not professor_id or not disciplina_id:
        return {"erro": "Professor e disciplina sao obrigatorios"}, 400

    db = session_factory()
    try:
        if not db.get(ProfessorModel, professor_id):
            return {"erro": "Professor nao encontrado"}, 404
        if not db.get(DisciplinaModel, disciplina_id):
            return {"erro": "Disciplina nao encontrada"}, 404

        db.add(
            ProfessorDisciplinaModel(
                professor_id=professor_id,
                disciplina_id=disciplina_id,
            )
        )
        db.commit()
        return {"mensagem": "Professor associado a disciplina"}, 201
    except IntegrityError:
        db.rollback()
        return {"erro": "Este professor ja esta associado a esta disciplina"}, 409
    finally:
        db.close()

def criar_turma(data, *, session_factory=get_session):
    nome = (data.get("nome") or "").strip()
    codigo = (data.get("codigo") or "").strip().upper()
    ano_letivo_raw = (data.get("ano_letivo") or "").strip()
    turno = (data.get("turno") or "").strip()

    if not nome or not codigo or not ano_letivo_raw:
        return {"erro": "Nome, codigo e ano letivo sao obrigatorios"}, 400

    try:
        ano_letivo = int(ano_letivo_raw)
    except ValueError:
        return {"erro": "Ano letivo deve ser um numero inteiro"}, 400

    if ano_letivo < 2000:
        return {"erro": "Ano letivo invalido"}, 400

    db = session_factory()
    try:
        turma = TurmaModel(
            nome=nome[:120],
            codigo=codigo[:30],
            ano_letivo=ano_letivo,
            turno=turno[:30] or None,
        )
        db.add(turma)
        db.commit()
        return {"id": turma.id}, 201
    except IntegrityError:
        db.rollback()
        return {"erro": "Codigo de turma ja cadastrado"}, 409
    finally:
        db.close()

def associar_aluno_turma(data, *, session_factory=get_session):
    aluno_id = data.get("aluno_id", type=int)
    turma_id = data.get("turma_id", type=int)

    if not aluno_id or not turma_id:
        return {"erro": "Aluno e turma sao obrigatorios"}, 400

    db = session_factory()
    try:
        if not db.get(AlunoModel, aluno_id):
            return {"erro": "Aluno nao encontrado"}, 404
        if not db.get(TurmaModel, turma_id):
            return {"erro": "Turma nao encontrada"}, 404

        db.add(AlunoTurmaModel(aluno_id=aluno_id, turma_id=turma_id))
        db.flush()
        from app.services.matriculas import sincronizar_turma
        sincronizar_turma(db, turma_id)
        db.commit()
        return {"mensagem": "Aluno associado a turma"}, 201
    except IntegrityError:
        db.rollback()
        return {"erro": "Este aluno ja esta associado a esta turma"}, 409
    finally:
        db.close()

def associar_professor_turma(data, *, session_factory=get_session):
    professor_id = data.get("professor_id", type=int)
    turma_id = data.get("turma_id", type=int)

    if not professor_id or not turma_id:
        return {"erro": "Professor e turma sao obrigatorios"}, 400

    db = session_factory()
    try:
        professor = db.get(ProfessorModel, professor_id)
        if not professor:
            return {"erro": "Professor nao encontrado"}, 404
        if not db.get(TurmaModel, turma_id):
            return {"erro": "Turma nao encontrada"}, 404

        disciplinas_professor = (
            db.query(ProfessorDisciplinaModel)
            .filter(ProfessorDisciplinaModel.professor_id == professor_id)
            .order_by(ProfessorDisciplinaModel.disciplina_id)
            .all()
        )
        if not disciplinas_professor:
            return {"erro": "Este professor nao possui disciplinas associadas"}, 400

        db.add(ProfessorTurmaModel(professor_id=professor_id, turma_id=turma_id))
        for vinculo in disciplinas_professor:
            insert_if_missing(db, TurmaDisciplinaModel,
                              turma_id=turma_id, disciplina_id=vinculo.disciplina_id)
        from app.services.matriculas import sincronizar_turma
        sincronizar_turma(db, turma_id)

        db.commit()
        return {"mensagem": "Professor associado a turma"}, 201
    except IntegrityError:
        db.rollback()
        return {"erro": "Este professor ja esta associado a esta turma"}, 409
    finally:
        db.close()
