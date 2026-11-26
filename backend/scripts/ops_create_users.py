"""Create staff accounts. Reads CREATE_USERS_JSON (a JSON list of
{"email", "password", "full_name", "role"}) and creates each one that does not
already exist; existing accounts are never changed. Prints only email
addresses, never a password."""
import json
import os

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User

users = json.loads(os.environ["CREATE_USERS_JSON"])
db = SessionLocal()
try:
    for entry in users:
        email = entry["email"].strip().lower()
        if db.query(User).filter(User.email == email).first():
            print(f"USER {email}: already exists, left unchanged")
            continue
        db.add(User(
            email=email,
            hashed_password=get_password_hash(entry["password"]),
            full_name=entry.get("full_name"),
            role=entry.get("role", "operator"),
            is_active=True,
            is_superuser=False,
        ))
        db.commit()
        print(f"USER {email}: created as {entry.get('role', 'operator')}")
finally:
    db.close()
