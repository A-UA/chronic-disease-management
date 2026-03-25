"""add_patient_id_to_documents

Revision ID: e7c4a1b29f10
Revises: d9a0b6e7f321
Create Date: 2026-03-25 16:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7c4a1b29f10"
down_revision: Union[str, Sequence[str], None] = "d9a0b6e7f321"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("patient_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_documents_patient_id"), "documents", ["patient_id"], unique=False)
    op.create_foreign_key(
        None,
        "documents",
        "patient_profiles",
        ["patient_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("documents_patient_id_fkey"), "documents", type_="foreignkey")
    op.drop_index(op.f("ix_documents_patient_id"), table_name="documents")
    op.drop_column("documents", "patient_id")
