from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.unidade_model import padrao_unidade


class DisciplinaModel(Base):
    __tablename__ = "disciplinas"
    __table_args__ = (
        UniqueConstraint("id", "unidade_id", name="uq_disciplina_id_unidade"),
        UniqueConstraint("unidade_id", "codigo", name="uq_disciplina_unidade_codigo"),
        Index("ix_disciplinas_unidade", "unidade_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    carga_horaria: Mapped[int] = mapped_column(Integer, nullable=False)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), nullable=False, default=padrao_unidade)

    documentos = relationship("DocumentoModel", back_populates="disciplina", foreign_keys="DocumentoModel.disciplina_id")
    notas = relationship("NotaModel", back_populates="disciplina")
