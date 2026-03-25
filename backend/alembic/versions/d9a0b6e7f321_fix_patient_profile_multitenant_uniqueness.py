"""fix_patient_profile_multitenant_uniqueness

Revision ID: d9a0b6e7f321
Revises: 5c8b4c7a9e21, 12c3eabda525
Create Date: 2026-03-25 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9a0b6e7f321"
down_revision: Union[str, Sequence[str], None] = ("5c8b4c7a9e21", "12c3eabda525")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE patient_profiles DROP CONSTRAINT IF EXISTS patient_profiles_user_id_key")
    op.execute("ALTER TABLE patient_profiles DROP CONSTRAINT IF EXISTS uq_patient_profiles_org_user")
    op.create_unique_constraint(
        "uq_patient_profiles_org_user",
        "patient_profiles",
        ["org_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_patient_profiles_org_user", "patient_profiles", type_="unique")
    op.create_unique_constraint("patient_profiles_user_id_key", "patient_profiles", ["user_id"])
