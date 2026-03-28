from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger
from sqlalchemy.sql import func
from datetime import datetime
from app.core.snowflake import get_next_id


class Base(DeclarativeBase):
    type_annotation_map = {
        int: BigInteger,
    }


class IDMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=get_next_id)


class UUIDMixin(IDMixin):
    """
    Deprecated: Using Snowflake ID (BigInteger) now, keep this name for compatibility 
    during migration but alias it to IDMixin.
    """
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
