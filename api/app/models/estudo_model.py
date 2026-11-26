"""Conteúdo didático privado por oferta, separado dos documentos pessoais."""
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ConteudoEstudoModel(Base):
    __tablename__ = 'estudo_conteudos'
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_disciplina_id: Mapped[int] = mapped_column(ForeignKey('turmas_disciplinas.id'), nullable=False)
    autor_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False, default='')
    link: Mapped[str] = mapped_column(String(2048), nullable=False, default='')
    arquivo: Mapped[str | None] = mapped_column(String(36), unique=True)
    mime: Mapped[str | None] = mapped_column(String(32))
    tamanho: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default='rascunho')
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    criado_em: Mapped[object] = mapped_column(DateTime, server_default=func.current_timestamp())
    __table_args__ = (
        CheckConstraint("tipo IN ('aviso','link','arquivo')", name='ck_estudo_tipo'),
        CheckConstraint("estado IN ('rascunho','publicado','arquivado')", name='ck_estudo_estado'),
        CheckConstraint('versao >= 1', name='ck_estudo_versao'),
        # 009 (U2b): PDF/PNG/JPEG até 5 MiB; vídeo MP4/WebM até 300 MiB.
        CheckConstraint("(tipo = 'arquivo' AND arquivo IS NOT NULL AND mime IS NOT NULL AND tamanho IS NOT NULL AND link = '' AND (tamanho BETWEEN 1 AND 5242880 OR (mime IN ('video/mp4', 'video/webm') AND tamanho BETWEEN 1 AND 314572800))) OR (tipo = 'link' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link <> '') OR (tipo = 'aviso' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link = '')", name='ck_estudo_recurso_video'),
        Index('ix_estudo_oferta_estado_id', 'turma_disciplina_id', 'estado', 'id'),
    )


class AuditoriaEstudoModel(Base):
    __tablename__ = 'estudo_auditoria'
    id: Mapped[int] = mapped_column(primary_key=True)
    conteudo_id: Mapped[int] = mapped_column(ForeignKey('estudo_conteudos.id'), nullable=False)
    ator_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    acao: Mapped[str] = mapped_column(String(30), nullable=False)
    criada_em: Mapped[object] = mapped_column(DateTime, server_default=func.current_timestamp())


class SecaoEstudoModel(Base):
    __tablename__ = 'estudo_secoes'
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_disciplina_id: Mapped[int] = mapped_column(ForeignKey('turmas_disciplinas.id'), nullable=False)
    autor_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default='ativa')
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (
        CheckConstraint("estado IN ('ativa','arquivada')", name='ck_estudo_secao_estado'),
        CheckConstraint('ordem BETWEEN 0 AND 9999', name='ck_estudo_secao_ordem'),
        CheckConstraint('versao >= 1', name='ck_estudo_secao_versao'),
        Index('ix_estudo_secao_oferta_ordem', 'turma_disciplina_id', 'ordem', 'id'),
    )


class ConteudoSecaoEstudoModel(Base):
    # Separate association preserves the MS02 schema and existing content.
    __tablename__ = 'estudo_conteudo_secao'
    conteudo_id: Mapped[int] = mapped_column(ForeignKey('estudo_conteudos.id'), primary_key=True)
    secao_id: Mapped[int] = mapped_column(ForeignKey('estudo_secoes.id'), nullable=False, index=True)


class AuditoriaSecaoEstudoModel(Base):
    __tablename__ = 'estudo_secao_auditoria'
    id: Mapped[int] = mapped_column(primary_key=True)
    secao_id: Mapped[int] = mapped_column(ForeignKey('estudo_secoes.id'), nullable=False)
    ator_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    acao: Mapped[str] = mapped_column(String(30), nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    criada_em: Mapped[object] = mapped_column(DateTime, server_default=func.current_timestamp())
