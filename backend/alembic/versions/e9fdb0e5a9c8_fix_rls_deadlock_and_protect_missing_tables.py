"""fix_rls_deadlock_and_protect_missing_tables

Revision ID: e9fdb0e5a9c8
Revises: 895b6555801a
Create Date: 2026-03-27 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e9fdb0e5a9c8'
down_revision: Union[str, Sequence[str], None] = '895b6555801a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. 为 messages 添加 org_id 并建立外键（因为之前没有这个字段，导致无法高效隔离）
    op.add_column('messages', sa.Column('org_id', sa.Uuid(), nullable=True))
    # 刷历史数据：通过 conversation_id 关联获取 org_id
    op.execute(
        "UPDATE messages m SET org_id = c.org_id "
        "FROM conversations c WHERE m.conversation_id = c.id AND m.org_id IS NULL"
    )
    op.alter_column('messages', 'org_id', nullable=False)
    op.create_foreign_key('fk_messages_org_id', 'messages', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_messages_org_id'), 'messages', ['org_id'], unique=False)

    # 2. 修复 organization_users 的 RLS 死锁
    # 允许用户查看自己的组织成员身份，即便还没设置 app.current_org_id
    op.execute("DROP POLICY IF EXISTS organization_users_isolation_policy ON organization_users")
    op.execute(
        "CREATE POLICY organization_users_isolation_policy ON organization_users "
        "USING ("
        "  org_id = current_setting('app.current_org_id', true)::UUID "
        "  OR user_id = current_setting('app.current_user_id', true)::UUID"
        ")"
    )

    # 3. 补全缺失的 RLS 保护
    missing_rls_tables = [
        "messages",
        "patient_family_links",
        "organization_invitations"
    ]
    
    # 特殊处理 patient_family_links (它没有 org_id 字段)
    op.execute("ALTER TABLE patient_family_links ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY patient_family_links_isolation_policy ON patient_family_links "
        "USING ("
        "  family_user_id = current_setting('app.current_user_id', true)::UUID "
        "  OR patient_id IN (SELECT id FROM patient_profiles WHERE org_id = current_setting('app.current_org_id', true)::UUID)"
        ")"
    )

    # 其他标准表
    for table in ["messages", "organization_invitations"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation_policy ON {table}")
        op.execute(
            f"CREATE POLICY {table}_isolation_policy ON {table} "
            f"USING (org_id = current_setting('app.current_org_id', true)::UUID)"
        )

def downgrade() -> None:
    # 撤销 RLS
    for table in ["messages", "patient_family_links", "organization_invitations"]:
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # 恢复 organization_users 的原始死锁策略
    op.execute("DROP POLICY IF EXISTS organization_users_isolation_policy ON organization_users")
    op.execute(
        "CREATE POLICY organization_users_isolation_policy ON organization_users "
        "USING (org_id = current_setting('app.current_org_id', true)::UUID)"
    )

    # 删除列
    op.drop_constraint('fk_messages_org_id', 'messages', type_='foreignkey')
    op.drop_index(op.f('ix_messages_org_id'), table_name='messages')
    op.drop_column('messages', 'org_id')
