from datetime import date
from sqlalchemy import func
from sqlalchemy import or_
from app.models import AlunoModel, AlunoTurmaModel, ComunicadoModel, DisciplinaModel, DocumentoModel, NotaModel, ProfessorDisciplinaModel, ProfessorModel, ProfessorTurmaModel, SolicitacaoDocumentoModel, TurmaDisciplinaModel, TurmaModel, UsuarioModel

def load_get_admin_data(db):
    total_alunos = db.query(func.count(AlunoModel.id)).scalar() or 0
    total_professores = db.query(func.count(ProfessorModel.id)).scalar() or 0
    matriculas_pendentes = db.query(func.count(AlunoModel.id)).filter(func.lower(func.coalesce(AlunoModel.status_matricula, '')) == 'pendente').scalar() or 0
    matriculas_hoje = db.query(func.count(AlunoModel.id)).filter(func.date(AlunoModel.created_at) == date.today()).scalar() or 0
    aluno_rows = db.query(AlunoModel, UsuarioModel.email).join(UsuarioModel, UsuarioModel.id == AlunoModel.usuario_id).order_by(AlunoModel.id.desc()).limit(100).all()
    professor_rows = db.query(ProfessorModel, UsuarioModel.email).join(UsuarioModel, UsuarioModel.id == ProfessorModel.usuario_id).order_by(ProfessorModel.id.desc()).limit(20).all()
    return {'total_alunos': total_alunos, 'total_professores': total_professores, 'matriculas_pendentes': matriculas_pendentes, 'matriculas_hoje': matriculas_hoje, 'aluno_rows': aluno_rows, 'professor_rows': professor_rows}


def load_get_aluno_detail(db, aluno_id):
    query = db.query(AlunoModel, UsuarioModel.email).join(UsuarioModel, UsuarioModel.id == AlunoModel.usuario_id)
    if aluno_id:
        aluno_row = query.filter(AlunoModel.id == aluno_id).first()
    else:
        aluno_row = query.order_by(AlunoModel.id.desc()).first()
    if not aluno_row:
        raise LookupError()
    aluno, email = aluno_row
    documentos = db.query(DocumentoModel).filter(DocumentoModel.aluno_id == aluno.id).order_by(DocumentoModel.id.desc()).limit(10).all()
    solicitacoes = db.query(SolicitacaoDocumentoModel).filter(SolicitacaoDocumentoModel.aluno_id == aluno.id).order_by(SolicitacaoDocumentoModel.id.desc()).limit(10).all()
    return {'aluno': aluno, 'email': email, 'documentos': documentos, 'solicitacoes': solicitacoes}


def load_get_professor_detail(db, professor_id):
    query = db.query(ProfessorModel, UsuarioModel.email).join(UsuarioModel, UsuarioModel.id == ProfessorModel.usuario_id)
    if professor_id:
        professor_row = query.filter(ProfessorModel.id == professor_id).first()
    else:
        professor_row = query.order_by(ProfessorModel.id.desc()).first()
    if not professor_row:
        raise LookupError()
    professor, email = professor_row
    disciplinas = db.query(ProfessorDisciplinaModel, DisciplinaModel).join(DisciplinaModel, DisciplinaModel.id == ProfessorDisciplinaModel.disciplina_id).filter(ProfessorDisciplinaModel.professor_id == professor.id).order_by(ProfessorDisciplinaModel.id.desc()).limit(10).all()
    documentos = db.query(DocumentoModel, AlunoModel, DisciplinaModel).join(AlunoModel, AlunoModel.id == DocumentoModel.aluno_id).join(DisciplinaModel, DisciplinaModel.id == DocumentoModel.disciplina_id).filter(DocumentoModel.professor_id == professor.id).order_by(DocumentoModel.id.desc()).limit(10).all()
    notas = db.query(NotaModel, AlunoModel, DisciplinaModel).join(AlunoModel, AlunoModel.id == NotaModel.aluno_id).join(DisciplinaModel, DisciplinaModel.id == NotaModel.disciplina_id).filter(NotaModel.professor_id == professor.id).order_by(NotaModel.id.desc()).limit(10).all()
    arquivos_professor = db.query(DocumentoModel, DisciplinaModel).join(DisciplinaModel, DisciplinaModel.id == DocumentoModel.disciplina_id).filter(DocumentoModel.professor_id == professor.id, DocumentoModel.aluno_id.is_(None)).order_by(DocumentoModel.id.desc()).limit(10).all()
    solicitacoes = db.query(SolicitacaoDocumentoModel).filter(SolicitacaoDocumentoModel.professor_id == professor.id).order_by(SolicitacaoDocumentoModel.id.desc()).limit(10).all()
    return {'professor': professor, 'email': email, 'disciplinas': disciplinas, 'documentos': documentos, 'notas': notas, 'arquivos_professor': arquivos_professor, 'solicitacoes': solicitacoes}


def search_students(db, identity, term):
    query = db.query(AlunoModel).outerjoin(AlunoTurmaModel, AlunoTurmaModel.aluno_id == AlunoModel.id).outerjoin(TurmaModel, TurmaModel.id == AlunoTurmaModel.turma_id)
    if not identity.admin:
        query = query.join(ProfessorTurmaModel, ProfessorTurmaModel.turma_id == TurmaModel.id).join(ProfessorModel, ProfessorModel.id == ProfessorTurmaModel.professor_id).filter(ProfessorModel.usuario_id == identity.id)
    def matches(column):
        return func.lower(column).contains(term.lower(), autoescape=True)
    filters = [matches(AlunoModel.nome), matches(AlunoModel.matricula), matches(TurmaModel.nome), matches(TurmaModel.codigo)]
    if identity.admin:
        filters.append(AlunoModel.cpf == term)
    return query.filter(or_(*filters)).distinct().order_by(AlunoModel.nome, AlunoModel.id).limit(20).all()
