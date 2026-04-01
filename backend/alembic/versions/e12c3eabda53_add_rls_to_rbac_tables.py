
"""add_rls_to_rbac_tables

Revision ID: e12c3eabda53
Revises: de7f2cd89913
Create Date: 2026-04-01 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e12c3eabda53'
down_revision: Union[str, Sequence[str], None] = 'de7f2cd89913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. 启用 RLS
    tables = ["roles", "role_permissions", "rbac_role_constraints", "organizations"]
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    
    # 2. 角色表隔离：当前组织 OR 系统角色 OR 用户所属组织的其它角色（用于支持超级管理员穿透加载）
    op.execute("""
        CREATE POLICY roles_isolation_policy ON roles
        USING (
            org_id = current_setting('app.current_org_id', true)::bigint 
            OR org_id IS NULL 
            OR org_id IN (
                SELECT org_id FROM organization_users 
                WHERE user_id = current_setting('app.current_user_id', true)::bigint
            )
        )
    """)

    # 3. 角色权限关联表隔离：跟随角色表的可见性
    op.execute("""
        CREATE POLICY role_permissions_isolation_policy ON role_permissions
        USING (role_id IN (SELECT id FROM roles))
    """)

    # 4. RBAC 约束表隔离
    op.execute("""
        CREATE POLICY rbac_role_constraints_isolation_policy ON rbac_role_constraints
        USING (
            org_id = current_setting('app.current_org_id', true)::bigint 
            OR org_id IS NULL 
            OR org_id IN (
                SELECT org_id FROM organization_users 
                WHERE user_id = current_setting('app.current_user_id', true)::bigint
            )
        )
    """)

    # 5. 组织表隔离：用户仅能看到自己所属的组织及其子树（暂定为所属组织，子树通过渗透逻辑访问）
    op.execute("""
        CREATE POLICY organizations_isolation_policy ON organizations
        USING (
            id IN (
                SELECT org_id FROM organization_users 
                WHERE user_id = current_setting('app.current_user_id', true)::bigint
            )
            OR id = current_setting('app.current_org_id', true)::bigint
        )
    """)

def downgrade() -> None:
    tables = ["roles", "role_permissions", "rbac_role_constraints", "organizations"]
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
