from datetime import date
from sqlalchemy import func
from app.models import AlunoModel, AlunoTurmaModel, ComunicadoModel, DisciplinaModel, DocumentoModel, NotaModel, ProfessorDisciplinaModel, ProfessorModel, ProfessorTurmaModel, SolicitacaoDocumentoModel, TurmaDisciplinaModel, TurmaModel, UsuarioModel

def load_get_comunicados(db, limit=8):
    comunicados = db.query(ComunicadoModel).order_by(ComunicadoModel.id.desc()).limit(limit).all()
    return {'comunicados': comunicados}
