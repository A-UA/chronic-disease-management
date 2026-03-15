from sqlalchemy import String, ForeignKey, Integer, BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from datetime import datetime
from .base import Base, UUIDMixin, TimestampMixin

class ApiKey(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_keys"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    qps_limit: Mapped[int] = mapped_column(Integer, default=10, server_default='10')
    token_quota: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    token_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default='0')
    
    status: Mapped[str] = mapped_column(String(50), default='active', server_default='active')
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
