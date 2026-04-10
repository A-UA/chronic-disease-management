from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin


class Menu(Base, IDMixin, TimestampMixin):
    __tablename__ = "menus"

    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("menus.id", ondelete="CASCADE"),
        nullable=True,
    )
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    org_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="菜单显示名称"
    )
    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="菜单唯一编码"
    )
    menu_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="page",
        comment="directory/page/link",
    )
    path: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="路由路径或外部URL"
    )
    icon: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="图标名称"
    )
    permission_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="关联权限编码",
    )
    sort: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    is_visible: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="侧边栏是否显示"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    meta: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="扩展元信息"
    )

    # 自引用关系
    children: Mapped[list[Menu]] = relationship(
        "Menu",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Menu.sort",
    )
    parent: Mapped[Menu | None] = relationship(
        "Menu",
        back_populates="children",
        remote_side="Menu.id",
    )

    __table_args__ = (
        Index("idx_menus_parent_sort", "parent_id", "sort"),
        Index("idx_menus_tenant_id", "tenant_id"),
    )
