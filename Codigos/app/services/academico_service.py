from datetime import date

from flask import abort
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.services.arquivos_service import _remove_saved_file, _save_profile_photo
from app.database import get_session
from app.concurrency import check_version, begin_submission, finish_submission
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

        # Turma com matérias registradas: o professor só leciona as que ela já tem, sem trazer
        # outras matérias dele. Turma ainda sem matérias mantém o fluxo antigo e recebe as dele.
        da_turma = {d for d, in db.query(TurmaDisciplinaModel.disciplina_id).filter_by(turma_id=turma_id)}
        do_professor = {vinculo.disciplina_id for vinculo in disciplinas_professor}
        if da_turma and not da_turma & do_professor:
            return {"erro": "Este professor nao leciona nenhuma materia desta turma. "
                            "Registre antes a turma na materia dele."}, 400

        db.add(ProfessorTurmaModel(professor_id=professor_id, turma_id=turma_id))
        if not da_turma:
            from app.services.matriculas import registrar_disciplina
            for disciplina_id in sorted(do_professor):
                registrar_disciplina(db, turma_id, disciplina_id)

        db.commit()
        return {"mensagem": "Professor associado a turma"}, 201
    except IntegrityError:
        db.rollback()
        return {"erro": "Este professor ja esta associado a esta turma"}, 409
    finally:
        db.close()


def registrar_turma_disciplina(data, *, session_factory=get_session):
    """Registra a turma inteira na matéria: todos os alunos dela passam a cursá-la."""
    turma_id = data.get("turma_id", type=int)
    disciplina_id = data.get("disciplina_id", type=int)

    if not turma_id or not disciplina_id:
        return {"erro": "Turma e materia sao obrigatorias"}, 400

    from app.services.cursos import turma_ativa
    from app.services.matriculas import registrar_disciplina
    db = session_factory()
    try:
        if not db.get(TurmaModel, turma_id):
            return {"erro": "Turma nao encontrada"}, 404
        if not db.get(DisciplinaModel, disciplina_id):
            return {"erro": "Materia nao encontrada"}, 404
        if not turma_ativa(db, turma_id):
            return {"erro": "Turma arquivada: nao recebe novas materias"}, 409
        if db.query(TurmaDisciplinaModel.id).filter_by(turma_id=turma_id, disciplina_id=disciplina_id).first():
            return {"erro": "Esta turma ja esta registrada nesta materia"}, 409

        registrar_disciplina(db, turma_id, disciplina_id)
        db.commit()
        return {"mensagem": "Turma registrada na materia"}, 201
    finally:
        db.close()


def retirar_turma_disciplina(data, *, session_factory=get_session):
    """Retira a matéria da turma enquanto ela ainda não tem histórico."""
    turma_id = data.get("turma_id", type=int)
    disciplina_id = data.get("disciplina_id", type=int)

    if not turma_id or not disciplina_id:
        return {"erro": "Turma e materia sao obrigatorias"}, 400

    from app.services.matriculas import historico_da_disciplina, retirar_disciplina
    db = session_factory()
    try:
        vinculo = (db.query(TurmaDisciplinaModel)
                   .filter_by(turma_id=turma_id, disciplina_id=disciplina_id)
                   .with_for_update().first())
        if not vinculo:
            return {"erro": "Esta turma nao esta registrada nesta materia"}, 404
        if historico_da_disciplina(db, vinculo.id):
            return {"erro": "A materia ja tem notas, chamadas, materiais, cursos ou professor atribuido "
                            "nesta turma e nao pode ser retirada. O historico fica preservado."}, 409

        retirar_disciplina(db, vinculo)
        db.commit()
        return {"mensagem": "Materia retirada da turma"}, 201
    finally:
        db.close()
