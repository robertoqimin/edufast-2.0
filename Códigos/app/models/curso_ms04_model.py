"""Extensões opcionais MS04. Startup não executa DDL."""
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CursoVersaoModel(Base):
    __tablename__ = 'curso_versoes'
    id: Mapped[int] = mapped_column(primary_key=True)
    curso_id: Mapped[int] = mapped_column(ForeignKey('cursos.id'), unique=True, nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (CheckConstraint('versao >= 1', name='ck_curso_versao_positiva'),)


class AulaConteudoCursoModel(Base):
    __tablename__ = 'curso_aula_conteudos'
    aula_id: Mapped[int] = mapped_column(ForeignKey('curso_aulas.id'), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False, default='')
    __table_args__ = (
        CheckConstraint("tipo IN ('video','texto')", name='ck_curso_aula_tipo'),
        CheckConstraint("tipo <> 'texto' OR length(trim(corpo)) > 0", name='ck_curso_aula_texto'),
    )


class RetomadaCursoModel(Base):
    __tablename__ = 'curso_retomadas'
    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey('alunos.id'), nullable=False)
    oferta_id: Mapped[int] = mapped_column(ForeignKey('curso_ofertas.id'), nullable=False)
    aula_id: Mapped[int] = mapped_column(ForeignKey('curso_aulas.id'), nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    atualizado_em: Mapped[object] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    __table_args__ = (
        UniqueConstraint('aluno_id','oferta_id', name='uq_curso_retomada_aluno_oferta'),
        CheckConstraint('versao >= 0', name='ck_curso_retomada_versao'),
    )


class RecursoAulaCursoModel(Base):
    __tablename__ = 'curso_aula_recursos'
    id: Mapped[int] = mapped_column(primary_key=True)
    aula_id: Mapped[int] = mapped_column(ForeignKey('curso_aulas.id'), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    link: Mapped[str] = mapped_column(String(2048), nullable=False, default='')
    arquivo: Mapped[str | None] = mapped_column(String(36))
    mime: Mapped[str | None] = mapped_column(String(32))
    tamanho: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default='ativo')
    __table_args__ = (
        CheckConstraint("estado IN ('ativo','arquivado')", name='ck_curso_recurso_estado'),
        CheckConstraint("(tipo = 'arquivo' AND arquivo IS NOT NULL AND mime IS NOT NULL AND tamanho BETWEEN 1 AND 5242880 AND tamanho IS NOT NULL AND link = '') OR (tipo = 'link' AND arquivo IS NULL AND mime IS NULL AND tamanho IS NULL AND link <> '')", name='ck_curso_recurso_tipo'),
    )
