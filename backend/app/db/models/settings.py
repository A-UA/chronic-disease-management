from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin

class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
