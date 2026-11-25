from sqlalchemy import Column, String, Text
from app.core.database import Base
from app.models.base import TimestampMixin


class AppSetting(Base, TimestampMixin):
    """Small key/value store for settings staff change from the app itself
    (e.g. the automatic-ordering switch), as opposed to deployment config."""
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
