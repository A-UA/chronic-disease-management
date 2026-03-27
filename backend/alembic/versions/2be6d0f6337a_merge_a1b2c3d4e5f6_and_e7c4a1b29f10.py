"""merge a1b2c3d4e5f6 and e7c4a1b29f10

Revision ID: 2be6d0f6337a
Revises: a1b2c3d4e5f6, e7c4a1b29f10
Create Date: 2026-03-27 22:12:47.213149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2be6d0f6337a'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'e7c4a1b29f10')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
