from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

from config import Config

engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
)
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def sqlite_connect(connection, _):
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def sqlite_begin(connection):
        connection.exec_driver_sql("BEGIN")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    return SessionLocal()


def init_db():
    """Validate production schema without executing DDL."""
    if Config.APP_ENV != "production":
        return
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in tables:
            raise RuntimeError(f"Esquema pendente de revisao/provisionamento: {table.name}")
        columns = {c["name"] for c in inspector.get_columns(table.name)}
        if set(table.columns.keys()) - columns:
            raise RuntimeError(f"Migracao revisada necessaria: {table.name}")
        unique = inspector.get_unique_constraints(table.name)
        unique += [i for i in inspector.get_indexes(table.name) if i.get("unique")]
        for constraint in table.constraints:
            if constraint.__class__.__name__ == "UniqueConstraint" and not any(
                set(item["column_names"]) == set(constraint.columns.keys()) for item in unique
            ):
                raise RuntimeError(f"Constraint ausente; executar preflight: {table.name}")
