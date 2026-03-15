from sqlalchemy import String, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from datetime import datetime
from .base import Base, UUIDMixin, TimestampMixin

class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), default='free', server_default='free')
    
    quota_tokens_limit: Mapped[int] = mapped_column(BigInteger, default=1000000, server_default='1000000')
    quota_tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default='0')

    # Relationships
    users: Mapped[list["OrganizationUser"]] = relationship(back_populates="organization")

class OrganizationUser(Base, TimestampMixin):
    __tablename__ = "organization_users"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), default='member', server_default='member') # owner, admin, member, viewer

    organization: Mapped["Organization"] = relationship(back_populates="users")
    user: Mapped["User"] = relationship(back_populates="organizations")

class OrganizationInvitation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organization_invitations"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    inviter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='pending', server_default='pending')
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
