"""add_composite_indexes_for_rls_performance

Revision ID: af7a0fa5ce51
Revises: 4c7042fd1801
Create Date: 2026-03-19 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'af7a0fa5ce51'
down_revision: Union[str, Sequence[str], None] = '4c7042fd1801'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Tables with (org_id, id)
    tables_with_id = [
        "knowledge_bases",
        "documents",
        "chunks",
        "conversations",
        "usage_logs",
        "api_keys",
        "organization_invitations",
        "manager_profiles",
        "patient_profiles",
        "management_suggestions"
    ]
    
    for table in tables_with_id:
        index_name = f"ix_{table}_org_id_id"
        op.create_index(index_name, table, ["org_id", "id"], unique=False)
    
    # Special cases for chunks
    op.create_index("ix_chunks_org_id_kb_id", "chunks", ["org_id", "kb_id"], unique=False)
    op.create_index("ix_chunks_org_id_document_id", "chunks", ["org_id", "document_id"], unique=False)

    # Tables with special composite keys
    # organization_users already has (org_id, user_id) as PK
    
    # patient_manager_assignments: (org_id, manager_id, patient_id)
    op.create_index("ix_patient_manager_assignments_org_id_composite", 
                    "patient_manager_assignments", 
                    ["org_id", "manager_id", "patient_id"], 
                    unique=False)

def downgrade() -> None:
    tables_with_id = [
        "knowledge_bases",
        "documents",
        "chunks",
        "conversations",
        "usage_logs",
        "api_keys",
        "organization_invitations",
        "manager_profiles",
        "patient_profiles",
        "management_suggestions"
    ]
    
    for table in tables_with_id:
        index_name = f"ix_{table}_org_id_id"
        op.drop_index(index_name, table_name=table)

    op.drop_index("ix_chunks_org_id_kb_id", table_name="chunks")
    op.drop_index("ix_chunks_org_id_document_id", table_name="chunks")
    op.drop_index("ix_patient_manager_assignments_org_id_composite", table_name="patient_manager_assignments")
