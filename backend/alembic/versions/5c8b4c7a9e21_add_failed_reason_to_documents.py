"""add failed_reason to documents

Revision ID: 5c8b4c7a9e21
Revises: 4c7042fd1801
Create Date: 2026-03-21 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5c8b4c7a9e21"
down_revision: Union[str, Sequence[str], None] = "4c7042fd1801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("failed_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "failed_reason")
