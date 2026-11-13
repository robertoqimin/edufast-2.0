"""Banco exclusivo da plataforma; nenhuma tabela pertence ao banco escolar."""
from datetime import datetime, timezone
from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME

precise_datetime = DateTime().with_variant(DATETIME(fsp=6), 'mysql')


class Base(DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = 'platform_owner'
    __table_args__ = (CheckConstraint('id = 1', name='ck_platform_single_owner'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    auth_version: Mapped[int] = mapped_column(Integer, default=1)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)


class School(Base):
    __tablename__ = 'platform_schools'
    __table_args__ = (CheckConstraint('monthly_cents >= 0', name='ck_platform_monthly'),
                     CheckConstraint("state IN ('pendente','ativa','suspensa')", name='ck_platform_school_state'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(31), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    domain: Mapped[str] = mapped_column(String(253), unique=True)
    state: Mapped[str] = mapped_column(String(20), default='pendente')
    monthly_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {'version_id_col': version}
    token_hash: Mapped[str | None] = mapped_column(String(64))
    captured_at: Mapped[datetime | None] = mapped_column(precise_datetime)
    synced_at: Mapped[datetime | None] = mapped_column(precise_datetime)


class Person(Base):
    __tablename__ = 'platform_people'
    __table_args__ = (UniqueConstraint('school_id', 'local_id', name='uq_platform_school_person'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('platform_schools.id'))
    local_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20))


class Movement(Base):
    __tablename__ = 'platform_movements'
    __table_args__ = (CheckConstraint('cents > 0', name='ck_platform_movement_positive'),
                     CheckConstraint("kind IN ('receita','despesa')", name='ck_platform_movement_kind'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('platform_schools.id'))
    request_key: Mapped[str] = mapped_column(String(36), unique=True)
    kind: Mapped[str] = mapped_column(String(12))
    cents: Mapped[int] = mapped_column(BigInteger)
    day: Mapped[datetime] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(200))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancellation_reason: Mapped[str | None] = mapped_column(String(200))


class Audit(Base):
    __tablename__ = 'platform_audit'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    actor: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(50))
    reference: Mapped[str] = mapped_column(String(80))
