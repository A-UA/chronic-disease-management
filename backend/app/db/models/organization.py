from sqlalchemy import String, ForeignKey, BigInteger, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from datetime import datetime
from typing import TYPE_CHECKING
from .base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .patient import PatientProfile
    from .rbac import Role

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
    
    # staff: admin/manager, patient: the actual patient user
    user_type: Mapped[str] = mapped_column(String(20), default='staff', server_default='staff') 

    organization: Mapped["Organization"] = relationship(back_populates="users")
    user: Mapped["User"] = relationship(back_populates="organizations")
    rbac_roles: Mapped[list["Role"]] = relationship(secondary="organization_user_roles")

class OrganizationUserRole(Base, TimestampMixin):
    __tablename__ = "organization_user_roles"

    org_id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ['org_id', 'user_id'],
            ['organization_users.org_id', 'organization_users.user_id'],
            ondelete="CASCADE"
        ),
    )

class OrganizationInvitation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organization_invitations"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    inviter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='pending', server_default='pending')
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

class PatientFamilyLink(Base, TimestampMixin):
    __tablename__ = "patient_family_links"

    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), primary_key=True)
    family_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    relationship_type: Mapped[str | None] = mapped_column(String(50)) # parents, spouse, etc.
    access_level: Mapped[int] = mapped_column(default=1) # 1: ViewOnly, 2: ProxyAction
    status: Mapped[str] = mapped_column(String(50), default='pending') # pending, active, rejected
    
    # Relationships
    family_user: Mapped["User"] = relationship()
    patient: Mapped["PatientProfile"] = relationship()
