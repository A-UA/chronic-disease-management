"""add updated_at column and missing indexes

Revision ID: a1b2c3d4e5f6
Revises: 895b6555801a
Create Date: 2026-03-27 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "895b6555801a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that use TimestampMixin
TIMESTAMP_TABLES = [
    "users",
    "organizations",
    "organization_users",
    "organization_user_roles",
    "organization_invitations",
    "patient_family_links",
    "knowledge_bases",
    "documents",
    "chunks",
    "conversations",
    "messages",
    "usage_logs",
    "api_keys",
    "patient_profiles",
    "manager_profiles",
    "patient_manager_assignments",
    "management_suggestions",
    "audit_logs",
    "roles",
    "role_permissions",
]


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add updated_at to all TimestampMixin tables
    for table in TIMESTAMP_TABLES:
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # 2. Add missing indexes for core query paths
    op.create_index("ix_conversations_org_id", "conversations", ["org_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_patient_profiles_user_id", "patient_profiles", ["user_id"])
    op.create_index(
        "ix_organization_invitations_org_id", "organization_invitations", ["org_id"]
    )
    op.create_index(
        "ix_organization_invitations_email", "organization_invitations", ["email"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove indexes
    op.drop_index(
        "ix_organization_invitations_email", table_name="organization_invitations"
    )
    op.drop_index(
        "ix_organization_invitations_org_id", table_name="organization_invitations"
    )
    op.drop_index("ix_patient_profiles_user_id", table_name="patient_profiles")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_index("ix_conversations_org_id", table_name="conversations")

    # Remove updated_at columns
    for table in TIMESTAMP_TABLES:
        op.drop_column(table, "updated_at")
