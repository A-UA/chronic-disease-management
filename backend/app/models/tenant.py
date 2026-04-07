"""租户模型：SaaS 多租户的计费主体与数据隔离边界"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .organization import Organization


class Tenant(Base, IDMixin, TimestampMixin):
    __tablename__ = "tenants"

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        server_default="active",
        comment="active / trial / suspended / archived",
    )
    plan_type: Mapped[str] = mapped_column(
        String(50),
        default="free",
        server_default="free",
        comment="free / pro / enterprise",
    )

    # 配额
    quota_tokens_limit: Mapped[int] = mapped_column(
        BigInteger, default=1_000_000, server_default="1000000"
    )
    quota_tokens_used: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    max_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_patients: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 客户信息（预留，暂不做前端管理页面）
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="hospital / clinic / community_health",
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    trial_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    organizations: Mapped[list["Organization"]] = relationship(
        "Organization", back_populates="tenant"
    )
