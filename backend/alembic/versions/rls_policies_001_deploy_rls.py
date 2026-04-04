"""部署 RLS（行级安全）策略

Revision ID: rls_policies_001
Revises: d08f011b680f
Create Date: 2026-04-05
"""
from alembic import op

revision = "rls_policies_001"
down_revision = "d08f011b680f"
branch_labels = None
depends_on = None

# 所有含 tenant_id NOT NULL 的业务表
TENANT_TABLES = [
    "organizations",
    "organization_users",
    "organization_user_roles",
    "organization_invitations",
    "patient_profiles",
    "health_metrics",
    "manager_profiles",
    "patient_manager_assignments",
    "management_suggestions",
    "knowledge_bases",
    "documents",
    "chunks",
    "conversations",
    "messages",
    "usage_logs",
    "audit_logs",
    "api_keys",
]

# tenant_id 可为 NULL 的表（系统级角色 tenant_id=NULL）
NULLABLE_TENANT_TABLES = [
    "roles",
    "rbac_role_constraints",
]

# 需要跨租户家属穿透的表
FAMILY_LINK_TABLE = "patient_family_links"


def upgrade() -> None:
    # ── 1. 通用策略：只能看到自己租户的数据 ──
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # SELECT 策略
        op.execute(f"""
            CREATE POLICY tenant_isolation_select ON {table}
            FOR SELECT
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        # INSERT 策略
        op.execute(f"""
            CREATE POLICY tenant_isolation_insert ON {table}
            FOR INSERT
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        # UPDATE 策略
        op.execute(f"""
            CREATE POLICY tenant_isolation_update ON {table}
            FOR UPDATE
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        # DELETE 策略
        op.execute(f"""
            CREATE POLICY tenant_isolation_delete ON {table}
            FOR DELETE
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)

    # ── 2. 可为 NULL 的表：系统角色(tenant_id=NULL) 或 租户角色 ──
    for table in NULLABLE_TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_or_system_select ON {table}
            FOR SELECT
            USING (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        op.execute(f"""
            CREATE POLICY tenant_or_system_insert ON {table}
            FOR INSERT
            WITH CHECK (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        op.execute(f"""
            CREATE POLICY tenant_or_system_update ON {table}
            FOR UPDATE
            USING (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        op.execute(f"""
            CREATE POLICY tenant_or_system_delete ON {table}
            FOR DELETE
            USING (
                tenant_id IS NULL
                OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)

    # ── 3. 家属穿透策略 ──
    # patient_family_links 表允许：
    #   a) 本租户数据
    #   b) family_user_id == 当前用户（家属查看跨租户关联）
    op.execute(f"ALTER TABLE {FAMILY_LINK_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {FAMILY_LINK_TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY family_link_select ON {FAMILY_LINK_TABLE}
        FOR SELECT
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            OR family_user_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
        )
    """)
    op.execute(f"""
        CREATE POLICY family_link_insert ON {FAMILY_LINK_TABLE}
        FOR INSERT
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
        )
    """)
    op.execute(f"""
        CREATE POLICY family_link_update ON {FAMILY_LINK_TABLE}
        FOR UPDATE
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
        )
    """)
    op.execute(f"""
        CREATE POLICY family_link_delete ON {FAMILY_LINK_TABLE}
        FOR DELETE
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
        )
    """)

    # ── 4. 菜单表：系统菜单(tenant_id=NULL) 或 租户自定义菜单 ──
    op.execute("ALTER TABLE menus ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE menus FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY menu_visibility ON menus
        FOR SELECT
        USING (
            tenant_id IS NULL
            OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
        )
    """)
    op.execute("""
        CREATE POLICY menu_manage ON menus
        FOR ALL
        USING (
            tenant_id IS NULL
            OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
        )
        WITH CHECK (
            tenant_id IS NULL
            OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
        )
    """)

    # ── 5. 不启用 RLS 的表 ──
    # users: 全局用户，不按租户隔离（通过 organization_users 关联）
    # tenants: 租户自身元数据，不受 RLS 限制
    # rbac_resources / rbac_actions / permissions / role_permissions: 全局字典
    # password_reset_tokens: 全局
    # system_settings: 全局


def downgrade() -> None:
    all_tables = (
        TENANT_TABLES
        + NULLABLE_TENANT_TABLES
        + [FAMILY_LINK_TABLE, "menus"]
    )
    for table in all_tables:
        # 删除所有策略
        op.execute(f"""
            DO $$ DECLARE
                pol RECORD;
            BEGIN
                FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = '{table}'
                LOOP
                    EXECUTE format('DROP POLICY IF EXISTS %I ON {table}', pol.policyname);
                END LOOP;
            END $$;
        """)
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
