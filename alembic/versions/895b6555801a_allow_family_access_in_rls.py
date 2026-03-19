"""allow_family_access_in_rls

Revision ID: 895b6555801a
Revises: af7a0fa5ce51
Create Date: 2026-03-19 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '895b6555801a'
down_revision: Union[str, Sequence[str], None] = 'af7a0fa5ce51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Update patient_profiles policy
    op.execute("DROP POLICY IF EXISTS patient_profiles_isolation_policy ON patient_profiles")
    op.execute(
        "CREATE POLICY patient_profiles_isolation_policy ON patient_profiles "
        "USING ("
        "  org_id = current_setting('app.current_org_id', true)::UUID "
        "  OR id IN (SELECT patient_id FROM patient_family_links WHERE family_user_id = current_setting('app.current_user_id', true)::UUID AND status = 'active')"
        ")"
    )

    # Update management_suggestions policy
    op.execute("DROP POLICY IF EXISTS management_suggestions_isolation_policy ON management_suggestions")
    op.execute(
        "CREATE POLICY management_suggestions_isolation_policy ON management_suggestions "
        "USING ("
        "  org_id = current_setting('app.current_org_id', true)::UUID "
        "  OR patient_id IN (SELECT patient_id FROM patient_family_links WHERE family_user_id = current_setting('app.current_user_id', true)::UUID AND status = 'active')"
        ")"
    )

def downgrade() -> None:
    # Revert to simple org_id policy
    op.execute("DROP POLICY IF EXISTS patient_profiles_isolation_policy ON patient_profiles")
    op.execute(
        "CREATE POLICY patient_profiles_isolation_policy ON patient_profiles "
        "USING (org_id = current_setting('app.current_org_id', true)::UUID)"
    )

    op.execute("DROP POLICY IF EXISTS management_suggestions_isolation_policy ON management_suggestions")
    op.execute(
        "CREATE POLICY management_suggestions_isolation_policy ON management_suggestions "
        "USING (org_id = current_setting('app.current_org_id', true)::UUID)"
    )
