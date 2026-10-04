#!/usr/bin/env python3
"""
One-time admin script: updates the D&H supplier DB record to use the
production credentials from .env and resets the stale test-environment
scroll cursor.

Run once inside the backend container:
  docker exec sync_backend python scripts/update_dandh_credentials.py

Safe to re-run: subsequent runs detect that client_id already matches .env
and skip the update.
"""
import os, sys, json, logging

sys.path.insert(0, "/app")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from app.core.database import SessionLocal
from app.models.supplier import Supplier
from app.core.security import decrypt_credential, encrypt_credential

db = SessionLocal()
try:
    dandh = db.query(Supplier).filter(Supplier.id == 2).first()
    if not dandh:
        # Fallback: find by name
        dandh = db.query(Supplier).filter(Supplier.name.ilike("%d&h%")).first()
    if not dandh:
        logger.error("No D&H supplier record found in DB.")
        sys.exit(1)

    logger.info(f"Found supplier: ID={dandh.id} name={dandh.name!r}")

    # Read current DB credentials
    current_creds = {}
    if dandh.credentials_encrypted:
        decrypted = decrypt_credential(dandh.credentials_encrypted)
        if decrypted:
            try:
                current_creds = json.loads(decrypted)
            except Exception:
                pass
        else:
            try:
                current_creds = json.loads(dandh.credentials_encrypted)
            except Exception:
                pass

    logger.info(f"Current DB credentials: client_id={current_creds.get('client_id')!r} environment={current_creds.get('environment')!r}")

    # Get .env values
    env_client_id = os.environ.get("DANDH_CLIENT_ID", "").strip()
    env_client_secret = os.environ.get("DANDH_CLIENT_SECRET", "").strip()
    env_account = os.environ.get("DANDH_ACCOUNT_NUMBER", "3302610000").strip()
    env_tenant = os.environ.get("DANDH_TENANT", "dhus").strip()
    env_environment = os.environ.get("DANDH_ENVIRONMENT", "production").strip()

    if not env_client_id or not env_client_secret:
        logger.error("DANDH_CLIENT_ID or DANDH_CLIENT_SECRET not set in environment. Nothing updated.")
        sys.exit(1)

    if current_creds.get("client_id") == env_client_id and current_creds.get("environment") == env_environment:
        logger.info("DB credentials already match .env. No update needed.")
        sys.exit(0)

    # Build new credentials
    new_creds = {
        "client_id": env_client_id,
        "client_secret": env_client_secret,
        "account_number": env_account,
        "tenant": env_tenant,
        "environment": env_environment,
    }

    logger.info(
        f"Updating D&H credentials: client_id={current_creds.get('client_id')!r} "
        f"-> {env_client_id!r}, environment={current_creds.get('environment')!r} -> {env_environment!r}"
    )

    # Encrypt and store
    new_creds_json = json.dumps(new_creds)
    encrypted = encrypt_credential(new_creds_json)
    dandh.credentials_encrypted = encrypted

    # Reset scroll cursor — the old cursor was obtained from test.api.dandh.com
    # and will be rejected by api.dandh.com (different server, different session).
    # Clearing it forces the next sync to start from the beginning of the
    # production catalog rather than error-looping on the invalid cursor.
    old_cursor = dandh.catalog_sync_cursor
    dandh.catalog_sync_cursor = None
    dandh.catalog_sync_exhausted_at = None

    db.commit()
    logger.info(
        f"Updated successfully. Old scroll cursor ({repr(old_cursor)[:30]!r}) cleared. "
        f"Next sync will start from the beginning of the production catalog."
    )

finally:
    db.close()
