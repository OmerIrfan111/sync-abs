import base64
import datetime as dt
import gzip
import json
import logging
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import Date, DateTime, LargeBinary, Numeric, func, insert, select, text
from sqlalchemy.engine import Engine

from app.core.database import Base
import app.models  # noqa: F401  registers every table on Base.metadata

logger = logging.getLogger(__name__)

# Large history tables that nothing else depends on; they are not worth the
# space or the time. Everything else (users, stores and their encrypted
# credentials, suppliers, catalog, listings, orders and POs, rules, settings,
# alerts) is backed up.
EXCLUDED_TABLES = {"sync_logs", "product_shipping_history"}
BATCH = 1000
# Restore refuses to run unless these are empty, so it can never overwrite live data.
MUST_BE_EMPTY = ("users", "orders", "marketplaces", "suppliers", "products")


def _encode(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return {"__b64__": base64.b64encode(bytes(value)).decode()}
    return value


def _decode(column, value):
    if value is None:
        return None
    ctype = column.type
    if isinstance(ctype, DateTime) and isinstance(value, str):
        return dt.datetime.fromisoformat(value)
    if isinstance(ctype, Date) and not isinstance(ctype, DateTime) and isinstance(value, str):
        return dt.date.fromisoformat(value)
    if isinstance(ctype, Numeric) and not isinstance(value, Decimal):
        return Decimal(str(value))
    if isinstance(ctype, LargeBinary) and isinstance(value, dict) and "__b64__" in value:
        return base64.b64decode(value["__b64__"])
    return value


def _tables():
    return [t for t in Base.metadata.sorted_tables if t.name not in EXCLUDED_TABLES]


def export_database(engine: Engine, path: str) -> dict:
    """Writes every backed-up table to a gzipped JSON-lines file (parents
    before children) and returns a manifest with per-table row counts."""
    counts: Dict[str, int] = {}
    with engine.connect() as conn:
        if conn.dialect.name == "postgresql":
            # One consistent snapshot across all tables, even while the app runs.
            conn = conn.execution_options(isolation_level="REPEATABLE READ")
        with gzip.open(path, "wt", encoding="utf-8") as out:
            for table in _tables():
                n = 0
                for row in conn.execution_options(stream_results=True).execute(select(table)):
                    out.write(json.dumps({"t": table.name, "r": {k: _encode(v) for k, v in row._mapping.items()}}) + "\n")
                    n += 1
                counts[table.name] = n
        try:
            revision = conn.execute(text("select version_num from alembic_version")).scalar()
        except Exception:
            revision = None
    return {
        "format": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "revision": revision,
        "rows": sum(counts.values()),
        "counts": counts,
    }


def restore_database(engine: Engine, path: str, manifest: Optional[dict] = None) -> Dict[str, int]:
    """Loads a backup file into an EMPTY database (run `alembic upgrade head`
    on it first). Refuses to touch a database that already has data. If a
    manifest is given, the restored row counts must match it exactly."""
    tables = {t.name: t for t in _tables()}
    if not tables:
        raise RuntimeError("No tables are defined, so nothing can be restored.")
    restored: Dict[str, int] = {name: 0 for name in tables}

    with engine.begin() as conn:
        for name in MUST_BE_EMPTY:
            if name in tables and conn.execute(select(func.count()).select_from(tables[name])).scalar():
                raise RuntimeError(f"Refusing to restore: table '{name}' already has data. Restore only into an empty database.")

        pending_table, batch = None, []

        def flush():
            nonlocal batch
            if batch and pending_table is not None:
                conn.execute(insert(tables[pending_table]), batch)
                restored[pending_table] += len(batch)
            batch = []

        with gzip.open(path, "rt", encoding="utf-8") as src:
            for line in src:
                record = json.loads(line)
                name = record["t"]
                if name not in tables:
                    continue
                if name != pending_table or len(batch) >= BATCH:
                    flush()
                    pending_table = name
                cols = tables[name].c
                batch.append({k: _decode(cols[k], v) for k, v in record["r"].items() if k in cols})
            flush()

        if conn.dialect.name == "postgresql":
            for name, table in tables.items():
                pk = list(table.primary_key.columns)
                if len(pk) == 1 and pk[0].type.python_type is int:
                    col = pk[0].name
                    conn.execute(text(
                        f"select setval(pg_get_serial_sequence('{name}', '{col}'), "
                        f"coalesce((select max({col}) from {name}), 1), (select max({col}) from {name}) is not null)"
                    ))

    if sum(restored.values()) == 0:
        raise RuntimeError("The backup file contained no rows for any known table; nothing was restored.")

    if manifest:
        expected = manifest.get("counts", {})
        mismatched = {n: (restored.get(n, 0), c) for n, c in expected.items() if n in tables and restored.get(n, 0) != c}
        if mismatched:
            raise RuntimeError(f"Restore verification failed (restored, expected): {mismatched}")
    return restored
