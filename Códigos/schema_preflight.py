"""Read-only schema/duplicate report; never calls create_app, seed, or migrations."""
import json
import os

from sqlalchemy import create_engine, inspect, select, func


def main():
    url = os.environ.get("EDUFAST_REVIEW_DB_URL")
    if not url:
        raise SystemExit("Defina EDUFAST_REVIEW_DB_URL explicitamente; .env nao sera usado como destino")
    os.environ["DB_URL"] = url
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    from app.database import Base
    from app import models  # noqa: F401
    engine = create_engine(url)
    report = {"read_only": True, "tables": []}
    try:
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        with engine.connect() as connection:
            for table in Base.metadata.sorted_tables:
                item = {"table": table.name, "exists": table.name in existing}
                report["tables"].append(item)
                if not item["exists"]:
                    continue
                columns = {c["name"] for c in inspector.get_columns(table.name)}
                item["missing_columns"] = sorted(set(table.columns.keys()) - columns)
                unique = inspector.get_unique_constraints(table.name)
                unique += [i for i in inspector.get_indexes(table.name) if i.get("unique")]
                item["unique_checks"] = []
                for constraint in table.constraints:
                    if constraint.__class__.__name__ != "UniqueConstraint":
                        continue
                    names = list(constraint.columns.keys())
                    check = {"columns": names, "present": any(set(i["column_names"]) == set(names) for i in unique)}
                    if set(names) <= columns:
                        selected = [table.c[n] for n in names]
                        duplicates = select(func.count()).select_from(table).where(
                            *[c.is_not(None) for c in selected]).group_by(*selected).having(func.count() > 1).subquery()
                        check["duplicate_groups"] = connection.execute(select(func.count()).select_from(duplicates)).scalar_one()
                    item["unique_checks"].append(check)
        from schema_inventory import inventory
        report["migrations"] = inventory(engine)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
