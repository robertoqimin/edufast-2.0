from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.unidade_model import padrao_unidade


class TurmaModel(Base):
    __tablename__ = "turmas"
    __table_args__ = (
        UniqueConstraint("id", "unidade_id", name="uq_turma_id_unidade"),
        UniqueConstraint("unidade_id", "codigo", name="uq_turma_unidade_codigo"),
        Index("ix_turmas_unidade", "unidade_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False)
    turno: Mapped[str | None] = mapped_column(String(30), nullable=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), nullable=False, default=padrao_unidade)

    alunos = relationship("AlunoTurmaModel", back_populates="turma")
    disciplinas = relationship("TurmaDisciplinaModel", back_populates="turma", foreign_keys="TurmaDisciplinaModel.turma_id")
