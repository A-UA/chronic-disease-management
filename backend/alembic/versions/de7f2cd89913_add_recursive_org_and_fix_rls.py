"""add_recursive_org_and_fix_rls

Revision ID: de7f2cd89913
Revises: a24a8417991b
Create Date: 2026-04-01 22:19:51.826296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de7f2cd89913'
down_revision: Union[str, Sequence[str], None] = 'a24a8417991b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add parent_id to organizations
    op.add_column('organizations', sa.Column('parent_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_organizations_parent_id', 'organizations', 'organizations', ['parent_id'], ['id'], ondelete='SET NULL')

    # 2. Fix all RLS policies to use current_setting('...', true)::bigint
    policies = [
        ("knowledge_bases", "knowledge_bases_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("documents", "documents_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("chunks", "chunks_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("conversations", "conversations_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("usage_logs", "usage_logs_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("api_keys", "api_keys_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("manager_profiles", "manager_profiles_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("patient_manager_assignments", "patient_manager_assignments_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("patient_profiles", "patient_profiles_isolation_policy", "(org_id = current_setting('app.current_org_id', true)::bigint) OR (id IN ( SELECT patient_family_links.patient_id FROM patient_family_links WHERE ((patient_family_links.family_user_id = current_setting('app.current_user_id', true)::bigint) AND (patient_family_links.status = 'active'))))"),
        ("management_suggestions", "management_suggestions_isolation_policy", "(org_id = current_setting('app.current_org_id', true)::bigint) OR (patient_id IN ( SELECT patient_family_links.patient_id FROM patient_family_links WHERE ((patient_family_links.family_user_id = current_setting('app.current_user_id', true)::bigint) AND (patient_family_links.status = 'active'))))"),
        ("audit_logs", "audit_logs_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("messages", "messages_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
        ("organization_users", "organization_users_isolation_policy", "(org_id = current_setting('app.current_org_id', true)::bigint) OR (user_id = current_setting('app.current_user_id', true)::bigint)"),
        ("patient_family_links", "patient_family_links_isolation_policy", "(family_user_id = current_setting('app.current_user_id', true)::bigint) OR (patient_id IN ( SELECT patient_profiles.id FROM patient_profiles WHERE (patient_profiles.org_id = current_setting('app.current_org_id', true)::bigint)))"),
        ("organization_invitations", "organization_invitations_isolation_policy", "org_id = current_setting('app.current_org_id', true)::bigint"),
    ]

    for table, name, definition in policies:
        op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
        op.execute(f"CREATE POLICY {name} ON {table} USING ({definition})")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Restore original RLS policies (without the 'true' parameter and potentially using UUID if older, but we'll use bigint since it's the current state)
    policies = [
        ("knowledge_bases", "knowledge_bases_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("documents", "documents_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("chunks", "chunks_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("conversations", "conversations_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("usage_logs", "usage_logs_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("api_keys", "api_keys_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("manager_profiles", "manager_profiles_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("patient_manager_assignments", "patient_manager_assignments_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("patient_profiles", "patient_profiles_isolation_policy", "(org_id = current_setting('app.current_org_id')::bigint) OR (id IN ( SELECT patient_family_links.patient_id FROM patient_family_links WHERE ((patient_family_links.family_user_id = current_setting('app.current_user_id')::bigint) AND (patient_family_links.status = 'active'))))"),
        ("management_suggestions", "management_suggestions_isolation_policy", "(org_id = current_setting('app.current_org_id')::bigint) OR (patient_id IN ( SELECT patient_family_links.patient_id FROM patient_family_links WHERE ((patient_family_links.family_user_id = current_setting('app.current_user_id')::bigint) AND (patient_family_links.status = 'active'))))"),
        ("audit_logs", "audit_logs_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("messages", "messages_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
        ("organization_users", "organization_users_isolation_policy", "(org_id = current_setting('app.current_org_id')::bigint) OR (user_id = current_setting('app.current_user_id')::bigint)"),
        ("patient_family_links", "patient_family_links_isolation_policy", "(family_user_id = current_setting('app.current_user_id')::bigint) OR (patient_id IN ( SELECT patient_profiles.id FROM patient_profiles WHERE (patient_profiles.org_id = current_setting('app.current_org_id')::bigint)))"),
        ("organization_invitations", "organization_invitations_isolation_policy", "org_id = current_setting('app.current_org_id')::bigint"),
    ]

    for table, name, definition in policies:
        op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
        op.execute(f"CREATE POLICY {name} ON {table} USING ({definition})")

    # 2. Remove parent_id from organizations
    op.drop_constraint('fk_organizations_parent_id', 'organizations', type_='foreignkey')
    op.drop_column('organizations', 'parent_id')
