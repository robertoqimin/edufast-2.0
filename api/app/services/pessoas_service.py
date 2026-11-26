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


def _parse_optional_date(value):
    if not value:
        return None

    return date.fromisoformat(value)

def get_admin_data(*, session_factory=get_session):
    from app.repositories.pessoas_repository import load_get_admin_data
    from app.presenters.admin_presenter import present_get_admin_data
    db = session_factory()
    try:
        values = load_get_admin_data(db)
        return present_get_admin_data(**values)
    except LookupError:
        abort(404)
    finally:
        db.close()


def get_aluno_detail(aluno_id, *, session_factory=get_session):
    from app.repositories.pessoas_repository import load_get_aluno_detail
    from app.presenters.admin_presenter import present_get_aluno_detail
    db = session_factory()
    try:
        values = load_get_aluno_detail(db, aluno_id)
        return present_get_aluno_detail(**values)
    except LookupError:
        abort(404)
    finally:
        db.close()


def get_professor_detail(professor_id, *, session_factory=get_session):
    from app.repositories.pessoas_repository import load_get_professor_detail
    from app.presenters.admin_presenter import present_get_professor_detail
    db = session_factory()
    try:
        values = load_get_professor_detail(db, professor_id)
        return present_get_professor_detail(**values)
    except LookupError:
        abort(404)
    finally:
        db.close()


def update_student_data(aluno_id, data, files=None, *, session_factory=get_session, version_check=check_version):
    foto_perfil, upload_error = _save_profile_photo(files)
    if upload_error:
        return upload_error

    db = session_factory()
    try:
        aluno = db.get(AlunoModel, aluno_id)
        if not aluno:
            _remove_saved_file(foto_perfil)
            return {"erro": "Aluno não encontrado"}, 404

        version_check(aluno, data)
        usuario = db.get(UsuarioModel, aluno.usuario_id)
        if not usuario:
            _remove_saved_file(foto_perfil)
            return {"erro": "Usuário do aluno não encontrado"}, 404

        nome = (data.get("nome") or "").strip()
        email = (data.get("email") or "").strip()
        matricula = (data.get("matricula") or "").strip()

        if not nome or not email or not matricula:
            _remove_saved_file(foto_perfil)
            return {"erro": "Nome, e-mail e matrícula são obrigatórios"}, 400

        foto_antiga = aluno.foto_perfil
        aluno.nome = nome[:120]
        aluno.cpf = (data.get("cpf") or "").strip()[:14] or None
        aluno.matricula = matricula[:30]
        aluno.curso_serie = (data.get("curso_serie") or "").strip()[:80] or None
        aluno.status_matricula = (data.get("status_matricula") or "").strip()[:20] or None
        aluno.data_nascimento = _parse_optional_date(data.get("data_nascimento"))
        if foto_perfil:
            aluno.foto_perfil = foto_perfil
        usuario.email = email[:120]

        db.commit()
        if foto_perfil:
            _remove_saved_file(foto_antiga)
        return {"mensagem": "Dados do aluno atualizados"}, 200
    except ValueError:
        db.rollback()
        _remove_saved_file(foto_perfil)
        return {"erro": "Data de nascimento deve estar no formato YYYY-MM-DD"}, 400
    except IntegrityError:
        db.rollback()
        _remove_saved_file(foto_perfil)
        return {"erro": "E-mail, CPF ou matrícula já cadastrados"}, 409
    except Exception:
        db.rollback()
        _remove_saved_file(foto_perfil)
        raise
    finally:
        db.close()

def update_professor_data(professor_id, data, files=None, *, session_factory=get_session, version_check=check_version):
    foto_perfil, upload_error = _save_profile_photo(files)
    if upload_error:
        return upload_error

    db = session_factory()
    try:
        professor = db.get(ProfessorModel, professor_id)
        if not professor:
            _remove_saved_file(foto_perfil)
            return {"erro": "Professor não encontrado"}, 404

        version_check(professor, data)
        usuario = db.get(UsuarioModel, professor.usuario_id)
        if not usuario:
            _remove_saved_file(foto_perfil)
            return {"erro": "Usuário do professor não encontrado"}, 404

        nome = (data.get("nome") or "").strip()
        email = (data.get("email") or "").strip()
        cpf = (data.get("cpf") or "").strip()

        if not nome or not email or not cpf:
            _remove_saved_file(foto_perfil)
            return {"erro": "Nome, e-mail e CPF são obrigatórios"}, 400

        foto_antiga = professor.foto_perfil
        professor.nome = nome[:120]
        professor.cpf = cpf[:14]
        professor.telefone = (data.get("telefone") or "").strip()[:20] or None
        professor.disciplina_principal = (
            data.get("disciplina_principal") or ""
        ).strip()[:80] or None
        professor.formacao_academica = (
            data.get("formacao_academica") or ""
        ).strip()[:120] or None
        professor.regime_trabalho = (data.get("regime_trabalho") or "").strip()[:50] or None
        professor.data_admissao = _parse_optional_date(data.get("data_admissao"))
        if foto_perfil:
            professor.foto_perfil = foto_perfil
        usuario.email = email[:120]

        db.commit()
        if foto_perfil:
            _remove_saved_file(foto_antiga)
        return {"mensagem": "Dados do professor atualizados"}, 200
    except ValueError:
        db.rollback()
        _remove_saved_file(foto_perfil)
        return {"erro": "Data de admissao deve estar no formato YYYY-MM-DD"}, 400
    except IntegrityError:
        db.rollback()
        _remove_saved_file(foto_perfil)
        return {"erro": "E-mail ou CPF já cadastrados"}, 409
    except Exception:
        db.rollback()
        _remove_saved_file(foto_perfil)
        raise
    finally:
        db.close()
