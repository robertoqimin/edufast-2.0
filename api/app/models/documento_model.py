from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.unidade_model import padrao_pela_disciplina


class DocumentoModel(Base):
    __tablename__ = "documentos"
    __table_args__ = (ForeignKeyConstraint(["disciplina_id", "unidade_id"], ["disciplinas.id", "disciplinas.unidade_id"],
                                           name="fk_documento_disciplina_unidade"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aluno_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("alunos.id"), nullable=True)
    professor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("professores.id"), nullable=True)
    disciplina_id: Mapped[int] = mapped_column(Integer, ForeignKey("disciplinas.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    caminho_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    data_envio: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    unidade_id: Mapped[int] = mapped_column(Integer, nullable=False, default=padrao_pela_disciplina)

    aluno = relationship("AlunoModel", back_populates="documentos")
    professor = relationship("ProfessorModel", back_populates="documentos")
    disciplina = relationship("DisciplinaModel", back_populates="documentos", foreign_keys=[disciplina_id])
