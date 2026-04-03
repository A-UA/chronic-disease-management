"""merge_heads

Revision ID: 4aa7f5802d29
Revises: b1c2d3e4f5a6, d867a38ac709, e12c3eabda53
Create Date: 2026-04-04 00:10:56.538369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4aa7f5802d29'
down_revision: Union[str, Sequence[str], None] = ('b1c2d3e4f5a6', 'd867a38ac709', 'e12c3eabda53')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
