"""A storage filename is never an authorization capability."""
from app.models import (AlunoModel, AlunoTurmaModel, AtividadeModel, DocumentoModel,
                        ProfessorModel, ProfessorTurmaModel, TurmaDisciplinaModel)


def allowed_file(db, identity, filename, *, profile=False):
    if profile:
        aluno = db.query(AlunoModel).filter_by(foto_perfil=filename).first()
        professor = db.query(ProfessorModel).filter_by(foto_perfil=filename).first()
        owner = aluno or professor
        if owner is None:
            return False
        return identity.admin or owner.usuario_id == identity.id
    document = db.query(DocumentoModel).filter_by(caminho_arquivo=filename).first()
    activity = db.query(AtividadeModel).filter_by(caminho_arquivo=filename).first()
    if not document and not activity:
        return False
    if identity.admin:
        return True
    if identity.papel == "aluno":
        aluno = db.query(AlunoModel).filter_by(usuario_id=identity.id).first()
        if not aluno:
            return False
        return bool((document and document.aluno_id == aluno.id) or (activity and db.query(AlunoTurmaModel.id).filter_by(aluno_id=aluno.id, turma_id=activity.turma_id).first()))
    if identity.papel == "professor":
        professor = db.query(ProfessorModel).filter_by(usuario_id=identity.id).first()
        if not professor:
            return False
        if activity and activity.professor_id == professor.id:
            return db.query(ProfessorTurmaModel.id).filter_by(professor_id=professor.id, turma_id=activity.turma_id).first() is not None
        if document and document.professor_id == professor.id:
            if document.aluno_id is None:
                return True
            return (db.query(AlunoTurmaModel.id)
                    .join(ProfessorTurmaModel, ProfessorTurmaModel.turma_id == AlunoTurmaModel.turma_id)
                    .join(TurmaDisciplinaModel, TurmaDisciplinaModel.turma_id == AlunoTurmaModel.turma_id)
                    .filter(AlunoTurmaModel.aluno_id == document.aluno_id,
                            ProfessorTurmaModel.professor_id == professor.id,
                            TurmaDisciplinaModel.disciplina_id == document.disciplina_id).first()) is not None
    return False
