"""Restore a backup into an EMPTY database. Run `alembic upgrade head` on that
database first. Configured by environment variables (the Azure CLI can't pass
dash-arguments):

  RESTORE_SOURCE   a backup file path, or a blob name in the backup container
  RESTORE_CONFIRM  must be 'yes'
  DATABASE_URL     the database to restore INTO (an empty one)

Refuses to run if the target already has data.
"""
import json
import os
import sys
import tempfile

from app.core.database import engine
from app.services.backup_service import restore_database

CONTAINER = os.environ.get("BACKUP_CONTAINER", "db-backups")


def main() -> int:
    if os.environ.get("RESTORE_CONFIRM") != "yes":
        print("RESTORE refused: set RESTORE_CONFIRM=yes")
        return 2
    source = os.environ.get("RESTORE_SOURCE")
    if not source:
        print("RESTORE refused: set RESTORE_SOURCE")
        return 2

    manifest = None
    if not os.path.exists(source):
        from azure.storage.blob import BlobServiceClient
        service = BlobServiceClient.from_connection_string(os.environ["BACKUP_STORAGE_CONNECTION_STRING"])
        path = os.path.join(tempfile.gettempdir(), os.path.basename(source))
        with open(path, "wb") as out:
            out.write(service.get_blob_client(CONTAINER, source).download_blob().readall())
        try:
            manifest = json.loads(service.get_blob_client(CONTAINER, source + ".manifest.json").download_blob().readall())
        except Exception:
            manifest = None
        source = path
    else:
        manifest_path = source + ".manifest.json"
        if os.path.exists(manifest_path):
            manifest = json.load(open(manifest_path))

    try:
        restored = restore_database(engine, source, manifest)
    except Exception as exc:
        print(f"RESTORE FAILED: {exc}")
        return 1
    print(f"RESTORE ok: {sum(restored.values())} rows in {len(restored)} tables" + (" (verified against the manifest)" if manifest else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
