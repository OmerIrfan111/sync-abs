"""Nightly database backup. Run by the Azure backup job: python scripts/ops_backup.py

Exports everything that matters to a gzipped file, uploads it to Azure Blob
Storage (BACKUP_STORAGE_CONNECTION_STRING), checks the upload, then records the
result so the app can show it. With no storage configured it keeps the file in
BACKUP_LOCAL_DIR (default /tmp), which is how it's tested locally.
Any failure is recorded, raised as an in-app alert, and exits non-zero.
"""
import datetime as dt
import json
import os
import sys
import tempfile

from app.core.database import SessionLocal, engine
from app.services.alerts_service import BACKUP_PROBLEM, raise_alert, resolve_alerts
from app.services.app_settings_service import record_backup
from app.services.backup_service import export_database

CONTAINER = os.environ.get("BACKUP_CONTAINER", "db-backups")


def main() -> int:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"backup-{stamp}.jsonl.gz"
    local_dir = os.environ.get("BACKUP_LOCAL_DIR") or tempfile.gettempdir()
    path = os.path.join(local_dir, name)
    db = SessionLocal()
    try:
        manifest = export_database(engine, path)
        size = os.path.getsize(path)
        where = f"local file {path}"

        connection = os.environ.get("BACKUP_STORAGE_CONNECTION_STRING")
        if connection:
            from azure.storage.blob import BlobServiceClient
            service = BlobServiceClient.from_connection_string(connection)
            with open(path, "rb") as data:
                service.get_blob_client(CONTAINER, name).upload_blob(data, overwrite=False)
            service.get_blob_client(CONTAINER, name + ".manifest.json").upload_blob(json.dumps(manifest).encode(), overwrite=False)
            uploaded = service.get_blob_client(CONTAINER, name).get_blob_properties().size
            if uploaded != size:
                raise RuntimeError(f"Upload check failed: uploaded {uploaded} bytes but the file is {size}")
            where = f"Azure storage {CONTAINER}/{name}"
            os.remove(path)

        record_backup(db, "ok", f"{name}: {manifest['rows']} rows, {size / 1e6:.1f} MB")
        resolve_alerts(db, BACKUP_PROBLEM)
        print(f"BACKUP ok: {manifest['rows']} rows in {len(manifest['counts'])} tables, {size / 1e6:.1f} MB -> {where}")
        return 0
    except Exception as exc:
        db.rollback()
        try:
            record_backup(db, "failed", str(exc))
            raise_alert(db, BACKUP_PROBLEM, f"The nightly database backup failed: {exc}")
        except Exception:
            pass
        print(f"BACKUP FAILED: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
