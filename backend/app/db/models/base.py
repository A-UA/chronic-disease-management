from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from uuid import UUID, uuid4

class Base(DeclarativeBase):
    pass

class UUIDMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())
