"""Read-only summary of the configured database (tables, row counts, migration revision).

Run inside a deployed container to see what a database already holds before
migrating it: python scripts/ops_inspect_db.py
"""
import json

from sqlalchemy import create_engine, inspect, text

from app.core.config import settings

engine = create_engine(settings.get_database_url())
tables = sorted(inspect(engine).get_table_names())
out = {"tables": len(tables)}
with engine.connect() as conn:
    for name in ("alembic_version", "users", "suppliers", "marketplaces", "products", "supplier_products", "orders"):
        if name in tables:
            out[name] = conn.execute(text("select count(*) from " + name)).scalar()
    if "alembic_version" in tables:
        out["revision"] = conn.execute(text("select version_num from alembic_version")).scalar()
print("INSPECT " + json.dumps(out))
