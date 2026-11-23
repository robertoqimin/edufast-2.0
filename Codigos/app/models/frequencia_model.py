"""Importação explícita: o módulo não altera o esquema na inicialização do app."""
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.crypto import EncryptedLongText


class ChamadaModel(Base):
    __tablename__ = 'frequencia_chamadas'
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_disciplina_id: Mapped[int] = mapped_column(ForeignKey('turmas_disciplinas.id'), nullable=False)
    dia: Mapped[object] = mapped_column(Date, nullable=False)
    aula: Mapped[int] = mapped_column(Integer, nullable=False)
    revisao: Mapped[int] = mapped_column(Integer, nullable=False)
    anterior_id: Mapped[int | None] = mapped_column(ForeignKey('frequencia_chamadas.id'))
    autor_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default='pendente')
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    decidido_por: Mapped[int | None] = mapped_column(ForeignKey('usuarios.id'))
    motivo: Mapped[str] = mapped_column(EncryptedLongText(), default='')
    decisao_motivo: Mapped[str] = mapped_column(EncryptedLongText(), default='')
    criada_em: Mapped[object] = mapped_column(DateTime, server_default=func.current_timestamp())
    __table_args__ = (UniqueConstraint('turma_disciplina_id', 'dia', 'aula', 'revisao', name='uq_chamada_revisao'),
        CheckConstraint('aula >= 1 AND aula <= 20', name='ck_chamada_aula'),
        CheckConstraint("estado IN ('pendente','aprovada','rejeitada','substituida')", name='ck_chamada_estado'))


class PresencaModel(Base):
    __tablename__ = 'frequencia_presencas'
    id: Mapped[int] = mapped_column(primary_key=True)
    chamada_id: Mapped[int] = mapped_column(ForeignKey('frequencia_chamadas.id'), nullable=False)
    aluno_id: Mapped[int] = mapped_column(ForeignKey('alunos.id'), nullable=False)
    situacao: Mapped[str] = mapped_column(String(12), nullable=False)
    __table_args__ = (UniqueConstraint('chamada_id', 'aluno_id', name='uq_presenca_aluno'),
        CheckConstraint("situacao IN ('presente','falta')", name='ck_presenca_situacao'))


class AtestadoModel(Base):
    __tablename__ = 'frequencia_atestados'
    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey('alunos.id'), nullable=False, index=True)
    inicio: Mapped[object] = mapped_column(Date, nullable=False)
    fim: Mapped[object] = mapped_column(Date, nullable=False)
    arquivo: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    mime: Mapped[str] = mapped_column(String(30), nullable=False)
    enviado_por: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default='pendente')
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    decidido_por: Mapped[int | None] = mapped_column(ForeignKey('usuarios.id'))
    motivo: Mapped[str] = mapped_column(EncryptedLongText(), default='')
    criado_em: Mapped[object] = mapped_column(DateTime, server_default=func.current_timestamp())
    __table_args__ = (CheckConstraint('fim >= inicio', name='ck_atestado_datas'),
        CheckConstraint("estado IN ('pendente','aceito','rejeitado')", name='ck_atestado_estado'))


class AuditoriaFrequenciaModel(Base):
    __tablename__ = 'frequencia_auditoria'
    id: Mapped[int] = mapped_column(primary_key=True)
    ator_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'), nullable=False)
    acao: Mapped[str] = mapped_column(String(40), nullable=False)
    referencia: Mapped[int] = mapped_column(Integer, nullable=False)
    criada_em: Mapped[object] = mapped_column(DateTime, server_default=func.current_timestamp())
