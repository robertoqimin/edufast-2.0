from sqlalchemy import ForeignKey, Index, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.unidade_model import padrao_unidade


class SolicitacaoAlteracaoModel(Base):
    __tablename__ = "solicitacoes_alteracoes"
    __table_args__ = (Index("ix_solicitacoes_alteracoes_unidade", "unidade_id", "estado"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")
    recurso_pendente: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    arquivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decidido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    justificativa: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    decided_at: Mapped[str | None] = mapped_column(TIMESTAMP, nullable=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), nullable=False, default=padrao_unidade)
