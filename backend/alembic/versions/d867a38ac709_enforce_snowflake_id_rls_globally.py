"""enforce_snowflake_id_rls_globally

Revision ID: d867a38ac709
Revises: de7f2cd89913
Create Date: 2026-04-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd867a38ac709'
down_revision: Union[str, Sequence[str], None] = 'de7f2cd89913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """强制所有组织隔离表使用 bigint 适配的 RLS 策略"""
    
    # 定义带有 org_id 的标准业务表
    org_isolated_tables = [
        "knowledge_bases", "documents", "chunks", "conversations", 
        "usage_logs", "api_keys", "manager_profiles", 
        "patient_manager_assignments", "patient_profiles", 
        "management_suggestions", "audit_logs", "messages",
        "organization_invitations"
    ]
    
    for table in org_isolated_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation_policy ON {table}")
        # 特殊处理患者表（支持家属穿透）
        if table == "patient_profiles":
            op.execute(
                f"CREATE POLICY {table}_isolation_policy ON {table} USING ("
                f"  (org_id = current_setting('app.current_org_id', true)::bigint) OR "
                f"  (id IN (SELECT patient_id FROM patient_family_links WHERE family_user_id = current_setting('app.current_user_id', true)::bigint AND status = 'active'))"
                f")"
            )
        # 特殊处理建议表（支持家属穿透）
        elif table == "management_suggestions":
             op.execute(
                f"CREATE POLICY {table}_isolation_policy ON {table} USING ("
                f"  (org_id = current_setting('app.current_org_id', true)::bigint) OR "
                f"  (patient_id IN (SELECT patient_id FROM patient_family_links WHERE family_user_id = current_setting('app.current_user_id', true)::bigint AND status = 'active'))"
                f")"
            )
        else:
            op.execute(
                f"CREATE POLICY {table}_isolation_policy ON {table} USING (org_id = current_setting('app.current_org_id', true)::bigint)"
            )

    # 特殊处理 organization_users 表
    op.execute("DROP POLICY IF EXISTS organization_users_isolation_policy ON organization_users")
    op.execute(
        "CREATE POLICY organization_users_isolation_policy ON organization_users "
        "USING ("
        "  org_id = current_setting('app.current_org_id', true)::bigint "
        "  OR user_id = current_setting('app.current_user_id', true)::bigint"
        ")"
    )

    # 特殊处理 patient_family_links 表
    op.execute("DROP POLICY IF EXISTS patient_family_links_isolation_policy ON patient_family_links")
    op.execute(
        "CREATE POLICY patient_family_links_isolation_policy ON patient_family_links "
        "USING ("
        "  family_user_id = current_setting('app.current_user_id', true)::bigint "
        "  OR patient_id IN (SELECT id FROM patient_profiles WHERE org_id = current_setting('app.current_org_id', true)::bigint)"
        ")"
    )

def downgrade() -> None:
    """通常不建议降级 RLS 策略到 UUID，但在本地开发中提供回退"""
    pass
