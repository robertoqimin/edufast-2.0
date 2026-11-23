from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session as OrmSession, declarative_base, sessionmaker

from config import Config

pool_options = {}
if Config.SQLALCHEMY_DATABASE_URI.startswith("postgresql"):
    pool_options = dict(pool_size=Config.DB_POOL_SIZE,
                        max_overflow=Config.DB_MAX_OVERFLOW,
                        pool_timeout=Config.DB_POOL_TIMEOUT,
                        pool_recycle=Config.DB_POOL_RECYCLE)
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI,
                       pool_pre_ping=True, **pool_options)
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

_EXPLICIT_IDS = "_ids_explicitos_postgresql"


@event.listens_for(OrmSession, "before_flush")
def _register_explicit_ids(session, _context, _instances):
    """Note PostgreSQL tables receiving ORM rows with an explicit integer id.

    MySQL advances AUTO_INCREMENT past an explicit id; a PostgreSQL sequence does
    not, so the next generated id would collide. after_flush restores parity.
    """
    pending = None
    for instance in session.new:
        state = inspect(instance)
        columns = list(state.mapper.local_table.primary_key.columns)
        if len(columns) != 1 or columns[0].autoincrement is False:
            continue
        if session.get_bind(state.mapper).dialect.name != "postgresql":
            continue
        key = state.mapper.get_property_by_column(columns[0]).key
        if getattr(instance, key, None) is not None:
            pending = pending or session.info.setdefault(_EXPLICIT_IDS, set())
            pending.add((state.mapper.local_table, columns[0]))


@event.listens_for(OrmSession, "after_flush")
def _advance_sequences(session, _context):
    pending = session.info.pop(_EXPLICIT_IDS, None)
    if not pending:
        return
    for table, column in pending:
        connection = session.connection(bind_arguments={"clause": table.select()})
        quote = connection.dialect.identifier_preparer.quote
        sequence = connection.execute(text("SELECT pg_get_serial_sequence(:t, :c)"),
                                      {"t": table.fullname, "c": column.name}).scalar()
        if sequence is None:
            continue
        # Never move backwards: other sessions may already hold later values.
        # The sequence name comes from the catalog (already quoted), not from input.
        target = quote(table.name) if table.schema is None else quote(table.schema) + "." + quote(table.name)
        connection.execute(text(
            f"SELECT setval(CAST(:s AS regclass), GREATEST("
            f"(SELECT COALESCE(MAX({quote(column.name)}), 0) FROM {target}), "
            f"(SELECT last_value FROM {sequence}), 1))"), {"s": sequence})


def get_session():
    return SessionLocal()


def init_db():
    """Validate production schema without executing DDL."""
    if Config.APP_ENV != "production":
        return
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        # Optional new module: old installations keep their login until SQL review.
        # Existing optional tables are still checked; no startup DDL is performed.
        if table.name in {'estudo_conteudos', 'estudo_auditoria', 'estudo_secoes',
                          'estudo_conteudo_secao', 'estudo_secao_auditoria', 'curso_versoes',
                          'curso_aula_conteudos', 'curso_retomadas', 'curso_aula_recursos'} and table.name not in tables:
            continue
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
