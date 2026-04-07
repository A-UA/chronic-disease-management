from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IDMixin, TimestampMixin


class ApiKey(Base, IDMixin, TimestampMixin):
    __tablename__ = "api_keys"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True,
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    qps_limit: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    token_quota: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    token_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")

    status: Mapped[str] = mapped_column(
        String(50), default="active", server_default="active",
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
