from datetime import date
from sqlalchemy import func
from app.models import AlunoModel, AlunoTurmaModel, ComunicadoModel, DisciplinaModel, DocumentoModel, NotaModel, ProfessorDisciplinaModel, ProfessorModel, ProfessorTurmaModel, SolicitacaoDocumentoModel, TurmaDisciplinaModel, TurmaModel, UsuarioModel

def load_get_disciplinas(db):
    disciplinas = db.query(DisciplinaModel).order_by(DisciplinaModel.nome.asc()).all()
    return {'disciplinas': disciplinas}


def load_get_disciplinas_page_data(db):
    disciplinas = db.query(DisciplinaModel).order_by(DisciplinaModel.nome.asc()).all()
    professores = db.query(ProfessorModel).order_by(ProfessorModel.nome.asc()).limit(200).all()
    professor_vinculos = db.query(ProfessorDisciplinaModel, ProfessorModel, DisciplinaModel).join(ProfessorModel, ProfessorModel.id == ProfessorDisciplinaModel.professor_id).join(DisciplinaModel, DisciplinaModel.id == ProfessorDisciplinaModel.disciplina_id).order_by(ProfessorDisciplinaModel.id.desc()).limit(30).all()
    return {'disciplinas': disciplinas, 'professores': professores, 'professor_vinculos': professor_vinculos}


def load_get_turmas_page_data(db):
    turmas = db.query(TurmaModel).order_by(TurmaModel.nome.asc()).all()
    alunos = db.query(AlunoModel).order_by(AlunoModel.nome.asc()).limit(250).all()
    professores = db.query(ProfessorModel).order_by(ProfessorModel.nome.asc()).limit(250).all()
    professor_ids = [professor.id for professor in professores]
    disciplinas_por_professor = {professor.id: [] for professor in professores}
    if professor_ids:
        professor_disciplina_rows = db.query(ProfessorDisciplinaModel, DisciplinaModel).join(DisciplinaModel, DisciplinaModel.id == ProfessorDisciplinaModel.disciplina_id).filter(ProfessorDisciplinaModel.professor_id.in_(professor_ids)).order_by(DisciplinaModel.nome.asc()).all()
        for vinculo, disciplina in professor_disciplina_rows:
            disciplinas_por_professor.setdefault(vinculo.professor_id, []).append(disciplina.nome)
    aluno_vinculos = db.query(AlunoTurmaModel, AlunoModel, TurmaModel).join(AlunoModel, AlunoModel.id == AlunoTurmaModel.aluno_id).join(TurmaModel, TurmaModel.id == AlunoTurmaModel.turma_id).order_by(AlunoTurmaModel.id.desc()).limit(40).all()
    professor_vinculos = db.query(ProfessorTurmaModel, ProfessorModel, TurmaModel).join(ProfessorModel, ProfessorModel.id == ProfessorTurmaModel.professor_id).join(TurmaModel, TurmaModel.id == ProfessorTurmaModel.turma_id).order_by(ProfessorTurmaModel.id.desc()).limit(40).all()
    disciplina_vinculos = db.query(TurmaDisciplinaModel, TurmaModel, DisciplinaModel).join(TurmaModel, TurmaModel.id == TurmaDisciplinaModel.turma_id).join(DisciplinaModel, DisciplinaModel.id == TurmaDisciplinaModel.disciplina_id).order_by(TurmaDisciplinaModel.id.desc()).limit(40).all()
    return {'turmas': turmas, 'alunos': alunos, 'professores': professores, 'disciplinas_por_professor': disciplinas_por_professor, 'aluno_vinculos': aluno_vinculos, 'professor_vinculos': professor_vinculos, 'disciplina_vinculos': disciplina_vinculos}
