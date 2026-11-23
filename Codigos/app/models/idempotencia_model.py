from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IdempotenciaModel(Base):
    __tablename__ = "idempotencias"
    __table_args__ = (UniqueConstraint("ator", "operacao", "chave", name="uq_envio"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ator: Mapped[str] = mapped_column(String(40), nullable=False)
    operacao: Mapped[str] = mapped_column(String(100), nullable=False)
    chave: Mapped[str] = mapped_column(String(128), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status_http: Mapped[int] = mapped_column(Integer, nullable=False, default=201)
