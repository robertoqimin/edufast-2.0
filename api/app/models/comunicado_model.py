from sqlalchemy import ForeignKey, Index, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.unidade_model import padrao_unidade_ou_todas


class ComunicadoModel(Base):
    __tablename__ = "comunicados"
    __table_args__ = (Index("ix_comunicados_unidade", "unidade_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    destinatario: Mapped[str] = mapped_column(String(80), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    criado_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    # NULL = enviado pelo super admin para todas as unidades.
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidades.id"), nullable=True,
                                                   default=padrao_unidade_ou_todas)
