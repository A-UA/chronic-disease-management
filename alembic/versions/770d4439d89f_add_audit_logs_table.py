"""add_audit_logs_table

Revision ID: 770d4439d89f
Revises: 895b6555801a
Create Date: 2026-03-19 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '770d4439d89f'
down_revision: Union[str, Sequence[str], None] = '895b6555801a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('org_id', sa.Uuid(), nullable=True),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('resource_type', sa.String(length=100), nullable=False),
    sa.Column('resource_id', sa.Uuid(), nullable=True),
    sa.Column('details', sa.Text(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_org_id'), 'audit_logs', ['org_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)

    # Enable RLS
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY audit_logs_isolation_policy ON audit_logs "
        "USING (org_id = current_setting('app.current_org_id', true)::UUID)"
    )

def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_resource_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_org_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
