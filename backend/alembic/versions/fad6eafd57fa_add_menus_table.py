"""add_menus_table

Revision ID: fad6eafd57fa
Revises: 4aa7f5802d29
Create Date: 2026-04-04 00:13:06.429863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fad6eafd57fa'
down_revision: Union[str, Sequence[str], None] = '4aa7f5802d29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('menus',
    sa.Column('parent_id', sa.BigInteger(), nullable=True),
    sa.Column('org_id', sa.BigInteger(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False, comment='菜单显示名称'),
    sa.Column('code', sa.String(length=100), nullable=False, comment='菜单唯一编码'),
    sa.Column('menu_type', sa.String(length=20), nullable=False, comment='directory/page/link'),
    sa.Column('path', sa.String(length=255), nullable=True, comment='路由路径或外部URL'),
    sa.Column('icon', sa.String(length=50), nullable=True, comment='图标名称'),
    sa.Column('permission_code', sa.String(length=100), nullable=True, comment='关联权限编码'),
    sa.Column('sort', sa.Integer(), nullable=False, comment='排序'),
    sa.Column('is_visible', sa.Boolean(), nullable=False, comment='侧边栏是否显示'),
    sa.Column('is_enabled', sa.Boolean(), nullable=False, comment='是否启用'),
    sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='扩展元信息'),
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_id'], ['menus.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_index('idx_menus_org_id', 'menus', ['org_id'], unique=False)
    op.create_index('idx_menus_parent_sort', 'menus', ['parent_id', 'sort'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_menus_parent_sort', table_name='menus')
    op.drop_index('idx_menus_org_id', table_name='menus')
    op.drop_table('menus')
