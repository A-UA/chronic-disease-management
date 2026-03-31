from sqlalchemy import BigInteger, String, ForeignKey, Text, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, IDMixin, TimestampMixin
from typing import List, Optional

class Resource(Base, IDMixin):
    """系统受保护的资源定义 (例如: patient, document, knowledge_base)"""
    __tablename__ = "rbac_resources"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True) 
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True) # e.g. "patient"
    description: Mapped[Optional[str]] = mapped_column(Text)

    permissions: Mapped[List["Permission"]] = relationship(back_populates="resource", cascade="all, delete-orphan")

class Action(Base, IDMixin):
    """系统支持的操作定义 (例如: create, read, update, delete, export)"""
    __tablename__ = "rbac_actions"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True) # e.g. "read"
    description: Mapped[Optional[str]] = mapped_column(Text)

class Permission(Base, IDMixin):
    """权限点：资源 + 操作的组合 (例如: patient:read)"""
    __tablename__ = "permissions"

    resource_id: Mapped[int] = mapped_column(ForeignKey("rbac_resources.id", ondelete="CASCADE"), index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("rbac_actions.id", ondelete="CASCADE"), index=True)
    
    # 扩展属性
    permission_type: Mapped[str] = mapped_column(String(20), default="api", server_default="api") # api, menu, element
    name: Mapped[str] = mapped_column(String(100), index=True) # e.g. "查看患者"
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True) # e.g. "patient:read"
    
    # UI 映射：如果是菜单类型，存储路由、图标、排序等
    ui_metadata: Mapped[Optional[dict]] = mapped_column(JSONB) 

    # Relationships
    resource: Mapped["Resource"] = relationship(back_populates="permissions")
    action: Mapped["Action"] = relationship()
    roles: Mapped[List["Role"]] = relationship(secondary="role_permissions", back_populates="permissions")

    __table_args__ = (
        UniqueConstraint('resource_id', 'action_id', name='_resource_action_uc'),
    )

class Role(Base, IDMixin, TimestampMixin):
    """角色：支持继承与多租户隔离"""
    __tablename__ = "roles"

    org_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    parent_role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), index=True)
    
    name: Mapped[str] = mapped_column(String(100), index=True)
    code: Mapped[str] = mapped_column(String(100), index=True) 
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(default=False) 

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(secondary="role_permissions", back_populates="roles")
    parent_role: Mapped[Optional["Role"]] = relationship(remote_side="Role.id", backref="child_roles")
    
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

class RoleConstraint(Base, IDMixin, TimestampMixin):
    """责任分离约束 (SoD)"""
    __tablename__ = "rbac_role_constraints"

    org_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    constraint_type: Mapped[str] = mapped_column(String(20)) # SSD (Static), DSD (Dynamic)
    
    role_id_1: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    role_id_2: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))

    description: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint('role_id_1', 'role_id_2', 'constraint_type', name='_role_conflict_uc'),
    )
