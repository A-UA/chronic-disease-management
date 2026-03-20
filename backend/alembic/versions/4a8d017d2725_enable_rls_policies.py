"""enable_rls_policies

Revision ID: 4a8d017d2725
Revises: 97b0dadb3109
Create Date: 2026-03-16 20:53:23.974163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a8d017d2725'
down_revision: Union[str, Sequence[str], None] = '97b0dadb3109'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    tables = [
        "knowledge_bases",
        "documents",
        "chunks",
        "conversations",
        "usage_logs",
        "api_keys",
        "organization_invitations",
        "organization_users"
    ]
    
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_isolation_policy ON {table} "
            f"USING (org_id = current_setting('app.current_org_id', true)::UUID)"
        )


def downgrade() -> None:
    """Downgrade schema."""
    tables = [
        "knowledge_bases",
        "documents",
        "chunks",
        "conversations",
        "usage_logs",
        "api_keys",
        "organization_invitations",
        "organization_users"
    ]
    
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
