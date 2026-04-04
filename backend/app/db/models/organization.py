from sqlalchemy import (
    String, ForeignKey, BigInteger, ForeignKeyConstraint,
    Integer, Text, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import TYPE_CHECKING
from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .patient import PatientProfile
    from .rbac import Role
    from .tenant import Tenant


class Organization(Base, IDMixin, TimestampMixin):
    __tablename__ = "organizations"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active",
        comment="active / inactive / archived",
    )
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dept_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="clinical / administrative / support",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="organizations")
    parent: Mapped["Organization | None"] = relationship(
        remote_side="Organization.id", back_populates="children",
    )
    children: Mapped[list["Organization"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan",
    )
    users: Mapped[list["OrganizationUser"]] = relationship(
        back_populates="organization",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_org_tenant_code"),
        Index("idx_org_tenant_parent_sort", "tenant_id", "parent_id", "sort"),
    )


class OrganizationUser(Base, TimestampMixin):
    __tablename__ = "organization_users"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    user_type: Mapped[str] = mapped_column(
        String(20), default="staff", server_default="staff",
    )

    organization: Mapped["Organization"] = relationship(back_populates="users")
    user: Mapped["User"] = relationship(back_populates="organizations")
    rbac_roles: Mapped[list["Role"]] = relationship(secondary="organization_user_roles")


class OrganizationUserRole(Base, TimestampMixin):
    __tablename__ = "organization_user_roles"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "user_id"],
            ["organization_users.org_id", "organization_users.user_id"],
            ondelete="CASCADE",
        ),
    )


class OrganizationInvitation(Base, IDMixin, TimestampMixin):
    __tablename__ = "organization_invitations"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True,
    )
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", server_default="pending",
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)


class PatientFamilyLink(Base, TimestampMixin):
    __tablename__ = "patient_family_links"

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), primary_key=True,
    )
    family_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )

    relationship_type: Mapped[str | None] = mapped_column(
        String(50),
    )  # parents, spouse, etc.
    access_level: Mapped[int] = mapped_column(default=1)  # 1: ViewOnly, 2: ProxyAction
    status: Mapped[str] = mapped_column(
        String(50), default="pending",
    )  # pending, active, rejected

    # Relationships
    family_user: Mapped["User"] = relationship()
    patient: Mapped["PatientProfile"] = relationship()
