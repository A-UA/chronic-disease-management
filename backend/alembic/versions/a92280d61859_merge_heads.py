"""merge_heads

Revision ID: a92280d61859
Revises: e9fdb0e5a9c8
Create Date: 2026-03-28 00:13:16.142321

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a92280d61859'
down_revision: Union[str, Sequence[str], None] = ('2be6d0f6337a', 'e9fdb0e5a9c8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
