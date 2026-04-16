"""deploy RLS policies

Revision ID: rls_policies_001
Revises: 4cf086a0a0c3
Create Date: 2026-04-05
"""

from alembic import op

revision = "rls_policies_001"
down_revision = "4cf086a0a0c3"
branch_labels = None
depends_on = None

# tenant_id NOT NULL tables
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

# tenant_id nullable tables (system roles have tenant_id=NULL)
NULLABLE_TENANT_TABLES = [
    "roles",
    "rbac_role_constraints",
]

# no tenant_id column - isolation via patient_profiles FK
FAMILY_LINK_TABLE = "patient_family_links"


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_select ON {table}
            FOR SELECT
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        op.execute(f"""
            CREATE POLICY tenant_isolation_insert ON {table}
            FOR INSERT
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        op.execute(f"""
            CREATE POLICY tenant_isolation_update ON {table}
            FOR UPDATE
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)
        op.execute(f"""
            CREATE POLICY tenant_isolation_delete ON {table}
            FOR DELETE
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        """)

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

    # patient_family_links: no tenant_id, isolation via patient_profiles FK
    op.execute(f"ALTER TABLE {FAMILY_LINK_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {FAMILY_LINK_TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY family_link_select ON {FAMILY_LINK_TABLE}
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM patient_profiles pp
                WHERE pp.id = patient_id
                AND pp.tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
            OR family_user_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
        )
    """)
    op.execute(f"""
        CREATE POLICY family_link_insert ON {FAMILY_LINK_TABLE}
        FOR INSERT
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM patient_profiles pp
                WHERE pp.id = patient_id
                AND pp.tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        )
    """)
    op.execute(f"""
        CREATE POLICY family_link_update ON {FAMILY_LINK_TABLE}
        FOR UPDATE
        USING (
            EXISTS (
                SELECT 1 FROM patient_profiles pp
                WHERE pp.id = patient_id
                AND pp.tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        )
    """)
    op.execute(f"""
        CREATE POLICY family_link_delete ON {FAMILY_LINK_TABLE}
        FOR DELETE
        USING (
            EXISTS (
                SELECT 1 FROM patient_profiles pp
                WHERE pp.id = patient_id
                AND pp.tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::bigint
            )
        )
    """)

    # menus: system menus (tenant_id=NULL) or tenant custom menus
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


def downgrade() -> None:
    all_tables = TENANT_TABLES + NULLABLE_TENANT_TABLES + [FAMILY_LINK_TABLE, "menus"]
    for table in all_tables:
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
