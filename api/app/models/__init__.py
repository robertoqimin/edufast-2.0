"""Models da aplicacao."""

from .unidade_model import UnidadeModel, UsuarioUnidadeModel, TransferenciaUnidadeModel
from .configuracao_model import ConfiguracaoModel
from .curso_model import (CursoModel, CapituloModel, TemaModel, AulaModel, OfertaCursoModel,
                         ProgressoAulaModel, AtribuicaoDocenteModel, EstadoTurmaModel, AuditoriaCursoModel)
from .academico_model import PeriodoLetivoModel, AvaliacaoModel, LancamentoNotaModel, AuditoriaAcademicaModel
from .escola_model import (IdentidadeEscolaModel, CalendarioEscolaModel, EventoCalendarioModel,
                          PoliticaEscolaModel, RegraTurmaEscolaModel, RegraPeriodoEscolaModel)
from .privacidade_model import PedidoPrivacidadeModel, AuditoriaPrivacidadeModel, LimiteLoginModel
from .estudo_model import ConteudoEstudoModel, AuditoriaEstudoModel
from .estudo_model import SecaoEstudoModel, ConteudoSecaoEstudoModel, AuditoriaSecaoEstudoModel
from .curso_ms04_model import CursoVersaoModel, AulaConteudoCursoModel, RetomadaCursoModel, RecursoAulaCursoModel

from .idempotencia_model import IdempotenciaModel
from .solicitacao_alteracao_model import SolicitacaoAlteracaoModel
from .aluno_model import AlunoModel
from .aluno_disciplina_model import AlunoDisciplinaModel
from .aluno_turma_model import AlunoTurmaModel
from .atividade_model import AtividadeModel
from .comunicado_model import ComunicadoModel
from .disciplina_model import DisciplinaModel
from .documento_model import DocumentoModel
from .nota_model import NotaModel
from .professor_model import ProfessorModel
from .professor_disciplina_model import ProfessorDisciplinaModel
from .professor_turma_model import ProfessorTurmaModel
from .solicitacao_documento_model import SolicitacaoDocumentoModel
from .turma_model import TurmaModel
from .turma_disciplina_model import TurmaDisciplinaModel
from .usuario_model import UsuarioModel

__all__ = [
    "UnidadeModel",
    "UsuarioUnidadeModel",
    "TransferenciaUnidadeModel",
    "UsuarioModel",
    "ProfessorModel",
    "ProfessorDisciplinaModel",
    "ProfessorTurmaModel",
    "SolicitacaoDocumentoModel",
    "AlunoModel",
    "AlunoDisciplinaModel",
    "AlunoTurmaModel",
    "AtividadeModel",
    "ComunicadoModel",
    "DisciplinaModel",
    "DocumentoModel",
    "NotaModel",
    "TurmaModel",
    "TurmaDisciplinaModel",
]
