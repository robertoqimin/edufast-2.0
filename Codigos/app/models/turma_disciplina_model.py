from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.unidade_model import padrao_pela_turma


class TurmaDisciplinaModel(Base):
    __tablename__ = "turmas_disciplinas"
    __table_args__ = (
        UniqueConstraint("turma_id", "disciplina_id", name="uq_turma_disciplina"),
        # 010: turma e disciplina da MESMA unidade, garantido pelo banco.
        ForeignKeyConstraint(["turma_id", "unidade_id"], ["turmas.id", "turmas.unidade_id"],
                             name="fk_turma_disciplina_turma_unidade"),
        ForeignKeyConstraint(["disciplina_id", "unidade_id"], ["disciplinas.id", "disciplinas.unidade_id"],
                             name="fk_turma_disciplina_disciplina_unidade"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    turma_id: Mapped[int] = mapped_column(Integer, ForeignKey("turmas.id"), nullable=False)
    disciplina_id: Mapped[int] = mapped_column(Integer, ForeignKey("disciplinas.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    unidade_id: Mapped[int] = mapped_column(Integer, nullable=False, default=padrao_pela_turma)

    turma = relationship("TurmaModel", back_populates="disciplinas", foreign_keys=[turma_id])
    disciplina = relationship("DisciplinaModel", foreign_keys=[disciplina_id])
