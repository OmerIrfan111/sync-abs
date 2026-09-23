from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base
from app.models.base import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    # Phase 5: staff roles/permissions. "admin" can manage credentials, users,
    # and destructive actions (delete); "operator" can run day-to-day
    # operations (sync, publish, route orders, edit rules); "viewer" is
    # read-only. is_superuser is kept for backward compatibility and always
    # implies "admin" regardless of this field.
    role = Column(String(20), default="operator", nullable=False)
