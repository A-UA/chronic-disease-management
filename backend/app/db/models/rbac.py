from sqlalchemy import BigInteger, String, ForeignKey, Text, UniqueConstraint
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin
from typing import List

class Permission(Base, IDMixin):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True) # e.g. "View Patients"
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True) # e.g. "patient:view"
    description: Mapped[str | None] = mapped_column(Text)

    # Relationships
    roles: Mapped[List["Role"]] = relationship(secondary="role_permissions", back_populates="permissions")

class Role(Base, IDMixin, TimestampMixin):
    __tablename__ = "roles"

    # If org_id is NULL, it's a System Global Role (Owner, Admin, Member, etc.)
    # If org_id is set, it's a Custom Role created by that specific Organization
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    
    name: Mapped[str] = mapped_column(String(100), index=True)
    code: Mapped[str] = mapped_column(String(100), index=True) # e.g. "org_admin", "head_nurse"
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(default=False) # Protection for built-in roles

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(secondary="role_permissions", back_populates="roles")
    
    __table_args__ = (
        UniqueConstraint('org_id', 'code', name='_org_role_code_uc'),
    )

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
