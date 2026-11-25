"""One-off: load marketplace credentials into the configured database.

Reads a JSON list from the IMPORT_MARKETPLACES_JSON environment variable:
[{"name": "eBay", "credentials": {...}, "credentials_expires_at": "..."}]
Credentials are encrypted with this deployment's CREDENTIAL_ENCRYPTION_KEY
before being stored. Prints only store names and status, never a secret.
"""
import json
import os
from datetime import datetime

from app.core.database import SessionLocal
from app.core.security import encrypt_credential
from app.models.marketplace import Marketplace

entries = json.loads(os.environ["IMPORT_MARKETPLACES_JSON"])
db = SessionLocal()
try:
    for entry in entries:
        market = db.query(Marketplace).filter(Marketplace.name == entry["name"]).first()
        if not market:
            print(f"IMPORT {entry['name']}: no such marketplace row, skipped")
            continue
        market.credentials_encrypted = encrypt_credential(json.dumps(entry["credentials"]))
        expires = entry.get("credentials_expires_at")
        if expires:
            market.credentials_expires_at = datetime.fromisoformat(expires)
        db.commit()
        print(f"IMPORT {entry['name']}: credentials saved")
finally:
    db.close()
