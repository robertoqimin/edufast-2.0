from datetime import date

from flask import abort
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.controllers.auth_controller import _remove_saved_file, _save_profile_photo
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


def format_created_at(value):
    from app.presenters.admin_presenter import format_created_at as implementation
    return implementation(value)


def status_class(status):
    from app.presenters.admin_presenter import status_class as implementation
    return implementation(status)


def format_relative_date(value):
    from app.presenters.admin_presenter import format_relative_date as implementation
    return implementation(value, clock=date)


def get_admin_data():
    from app.services.pessoas_service import get_admin_data as implementation
    return implementation(session_factory=get_session)


def get_comunicados(limit=8):
    from app.services.comunicados_service import get_comunicados as implementation
    return implementation(limit, session_factory=get_session)


def criar_comunicado(data, criado_por=None):
    from app.services.comunicados_service import criar_comunicado as implementation
    return implementation(data, criado_por, session_factory=get_session)


def get_disciplinas():
    from app.services.academico_service import get_disciplinas as implementation
    return implementation(session_factory=get_session)


def get_disciplinas_page_data():
    from app.services.academico_service import get_disciplinas_page_data as implementation
    return implementation(session_factory=get_session)


def criar_disciplina(data):
    from app.services.academico_service import criar_disciplina as implementation
    return implementation(data, session_factory=get_session)


def associar_professor_disciplina(data):
    from app.services.academico_service import associar_professor_disciplina as implementation
    return implementation(data, session_factory=get_session)


def get_turmas_page_data():
    from app.services.academico_service import get_turmas_page_data as implementation
    return implementation(session_factory=get_session)


def criar_turma(data):
    from app.services.academico_service import criar_turma as implementation
    return implementation(data, session_factory=get_session)


def associar_aluno_turma(data):
    from app.services.academico_service import associar_aluno_turma as implementation
    return implementation(data, session_factory=get_session)


def associar_professor_turma(data):
    from app.services.academico_service import associar_professor_turma as implementation
    return implementation(data, session_factory=get_session)


def registrar_turma_disciplina(data):
    from app.services.academico_service import registrar_turma_disciplina as implementation
    return implementation(data, session_factory=get_session)


def retirar_turma_disciplina(data):
    from app.services.academico_service import retirar_turma_disciplina as implementation
    return implementation(data, session_factory=get_session)


def request_student_document(aluno_id, data):
    from app.services.documentos_service import request_student_document as implementation
    return implementation(aluno_id, data, session_factory=get_session)


def request_professor_document(professor_id, data):
    from app.services.documentos_service import request_professor_document as implementation
    return implementation(professor_id, data, session_factory=get_session)


def _parse_optional_date(value):
    from app.services.pessoas_service import _parse_optional_date as implementation
    return implementation(value)


def update_student_data(aluno_id, data, files=None):
    from app.services.pessoas_service import update_student_data as implementation
    return implementation(aluno_id, data, files, session_factory=get_session, version_check=check_version)


def update_professor_data(professor_id, data, files=None):
    from app.services.pessoas_service import update_professor_data as implementation
    return implementation(professor_id, data, files, session_factory=get_session, version_check=check_version)


def get_aluno_detail(aluno_id):
    from app.services.pessoas_service import get_aluno_detail as implementation
    return implementation(aluno_id, session_factory=get_session)


def get_professor_detail(professor_id):
    from app.services.pessoas_service import get_professor_detail as implementation
    return implementation(professor_id, session_factory=get_session)
