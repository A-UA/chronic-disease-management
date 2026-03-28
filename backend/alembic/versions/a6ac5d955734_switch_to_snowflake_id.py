"""switch_to_snowflake_id

Revision ID: a6ac5d955734
Revises: a92280d61859
Create Date: 2026-03-29 00:18:21.066808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a6ac5d955734'
down_revision: Union[str, Sequence[str], None] = 'a92280d61859'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DROP POLICY IF EXISTS knowledge_bases_isolation_policy ON knowledge_bases")
    op.execute("DROP POLICY IF EXISTS documents_isolation_policy ON documents")
    op.execute("DROP POLICY IF EXISTS chunks_isolation_policy ON chunks")
    op.execute("DROP POLICY IF EXISTS conversations_isolation_policy ON conversations")
    op.execute("DROP POLICY IF EXISTS usage_logs_isolation_policy ON usage_logs")
    op.execute("DROP POLICY IF EXISTS api_keys_isolation_policy ON api_keys")
    op.execute("DROP POLICY IF EXISTS manager_profiles_isolation_policy ON manager_profiles")
    op.execute("DROP POLICY IF EXISTS patient_manager_assignments_isolation_policy ON patient_manager_assignments")
    op.execute("DROP POLICY IF EXISTS patient_profiles_isolation_policy ON patient_profiles")
    op.execute("DROP POLICY IF EXISTS management_suggestions_isolation_policy ON management_suggestions")
    op.execute("DROP POLICY IF EXISTS audit_logs_isolation_policy ON audit_logs")
    op.execute("DROP POLICY IF EXISTS messages_isolation_policy ON messages")
    op.execute("DROP POLICY IF EXISTS organization_users_isolation_policy ON organization_users")
    op.execute("DROP POLICY IF EXISTS patient_family_links_isolation_policy ON patient_family_links")
    op.execute("DROP POLICY IF EXISTS organization_invitations_isolation_policy ON organization_invitations")
    op.execute("ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS api_keys_created_by_fkey")
    op.execute("ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS api_keys_org_id_fkey")
    op.execute("ALTER TABLE knowledge_bases DROP CONSTRAINT IF EXISTS knowledge_bases_created_by_fkey")
    op.execute("ALTER TABLE knowledge_bases DROP CONSTRAINT IF EXISTS knowledge_bases_org_id_fkey")
    op.execute("ALTER TABLE organization_invitations DROP CONSTRAINT IF EXISTS organization_invitations_inviter_id_fkey")
    op.execute("ALTER TABLE organization_invitations DROP CONSTRAINT IF EXISTS organization_invitations_org_id_fkey")
    op.execute("ALTER TABLE organization_users DROP CONSTRAINT IF EXISTS organization_users_org_id_fkey")
    op.execute("ALTER TABLE organization_users DROP CONSTRAINT IF EXISTS organization_users_user_id_fkey")
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_kb_id_fkey")
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_org_id_fkey")
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_user_id_fkey")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_kb_id_fkey")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_org_id_fkey")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_uploader_id_fkey")
    op.execute("ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_api_key_id_fkey")
    op.execute("ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_org_id_fkey")
    op.execute("ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_user_id_fkey")
    op.execute("ALTER TABLE chunks DROP CONSTRAINT IF EXISTS chunks_document_id_fkey")
    op.execute("ALTER TABLE chunks DROP CONSTRAINT IF EXISTS chunks_kb_id_fkey")
    op.execute("ALTER TABLE chunks DROP CONSTRAINT IF EXISTS chunks_org_id_fkey")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_conversation_id_fkey")
    op.execute("ALTER TABLE manager_profiles DROP CONSTRAINT IF EXISTS manager_profiles_org_id_fkey")
    op.execute("ALTER TABLE patient_profiles DROP CONSTRAINT IF EXISTS patient_profiles_org_id_fkey")
    op.execute("ALTER TABLE patient_family_links DROP CONSTRAINT IF EXISTS patient_family_links_family_user_id_fkey")
    op.execute("ALTER TABLE patient_family_links DROP CONSTRAINT IF EXISTS patient_family_links_patient_id_fkey")
    op.execute("ALTER TABLE patient_manager_assignments DROP CONSTRAINT IF EXISTS patient_manager_assignments_org_id_fkey")
    op.execute("ALTER TABLE management_suggestions DROP CONSTRAINT IF EXISTS management_suggestions_org_id_fkey")
    op.execute("ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_org_id_fkey")
    op.execute("ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_user_id_fkey")
    op.execute("ALTER TABLE roles DROP CONSTRAINT IF EXISTS roles_org_id_fkey")
    op.execute("ALTER TABLE role_permissions DROP CONSTRAINT IF EXISTS role_permissions_permission_id_fkey")
    op.execute("ALTER TABLE role_permissions DROP CONSTRAINT IF EXISTS role_permissions_role_id_fkey")
    op.execute("ALTER TABLE organization_user_roles DROP CONSTRAINT IF EXISTS organization_user_roles_role_id_fkey")
    op.execute("ALTER TABLE management_suggestions DROP CONSTRAINT IF EXISTS management_suggestions_patient_id_fkey")
    op.execute("ALTER TABLE management_suggestions DROP CONSTRAINT IF EXISTS management_suggestions_manager_id_fkey")
    op.execute("ALTER TABLE manager_profiles DROP CONSTRAINT IF EXISTS manager_profiles_user_id_fkey")
    op.execute("ALTER TABLE patient_manager_assignments DROP CONSTRAINT IF EXISTS patient_manager_assignments_patient_id_fkey")
    op.execute("ALTER TABLE patient_manager_assignments DROP CONSTRAINT IF EXISTS patient_manager_assignments_manager_id_fkey")
    op.execute("ALTER TABLE patient_profiles DROP CONSTRAINT IF EXISTS patient_profiles_user_id_fkey")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_patient_id_fkey")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS fk_messages_org_id")
    op.execute("ALTER TABLE organization_user_roles DROP CONSTRAINT IF EXISTS organization_user_roles_org_id_user_id_fkey")
    # --- Alter Columns ---
    op.alter_column('api_keys', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('api_keys', 'created_by',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(created_by::text), 1, 16))::bit(64)::bigint")
    op.alter_column('api_keys', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('audit_logs', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=True, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('audit_logs', 'user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('audit_logs', 'resource_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=True, postgresql_using="('x' || substr(md5(resource_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('audit_logs', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.add_column('chunks', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('chunks', sa.Column('tsv_content', postgresql.TSVECTOR(), nullable=True))
    op.alter_column('chunks', 'kb_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(kb_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('chunks', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('chunks', 'document_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(document_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('chunks', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.create_index('idx_chunk_tsv', 'chunks', ['tsv_content'], unique=False, postgresql_using='gin')
    op.alter_column('conversations', 'kb_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(kb_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('conversations', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('conversations', 'user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('conversations', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('documents', 'kb_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(kb_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('documents', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('documents', 'uploader_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(uploader_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('documents', 'patient_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=True, postgresql_using="('x' || substr(md5(patient_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('documents', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('knowledge_bases', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('knowledge_bases', 'created_by',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(created_by::text), 1, 16))::bit(64)::bigint")
    op.alter_column('knowledge_bases', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('management_suggestions', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('management_suggestions', 'manager_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(manager_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('management_suggestions', 'patient_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(patient_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('management_suggestions', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('manager_profiles', 'user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('manager_profiles', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('manager_profiles', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('messages', 'conversation_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(conversation_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('messages', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('messages', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_invitations', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_invitations', 'inviter_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(inviter_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_invitations', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_user_roles', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_user_roles', 'user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_user_roles', 'role_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(role_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_users', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organization_users', 'user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('organizations', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_family_links', 'patient_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(patient_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_family_links', 'family_user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(family_user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_family_links', 'access_level',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(access_level::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_manager_assignments', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_manager_assignments', 'manager_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(manager_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_manager_assignments', 'patient_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(patient_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_profiles', 'user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_profiles', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('patient_profiles', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('permissions', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('role_permissions', 'role_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(role_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('role_permissions', 'permission_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(permission_id::text), 1, 16))::bit(64)::bigint")
    op.drop_column('role_permissions', 'updated_at')
    op.alter_column('roles', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=True, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('roles', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('usage_logs', 'org_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(org_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('usage_logs', 'user_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=True, postgresql_using="('x' || substr(md5(user_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('usage_logs', 'api_key_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=True, postgresql_using="('x' || substr(md5(api_key_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('usage_logs', 'resource_id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=True, postgresql_using="('x' || substr(md5(resource_id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('usage_logs', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    op.alter_column('users', 'id',
               existing_type=sa.UUID(),
               type_=sa.BigInteger(),
               existing_nullable=False, postgresql_using="('x' || substr(md5(id::text), 1, 16))::bit(64)::bigint")
    # --- Restore Foreign Keys ---
    op.execute("ALTER TABLE api_keys ADD CONSTRAINT api_keys_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id)")
    op.execute("ALTER TABLE api_keys ADD CONSTRAINT api_keys_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE knowledge_bases ADD CONSTRAINT knowledge_bases_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id)")
    op.execute("ALTER TABLE knowledge_bases ADD CONSTRAINT knowledge_bases_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE organization_invitations ADD CONSTRAINT organization_invitations_inviter_id_fkey FOREIGN KEY (inviter_id) REFERENCES users(id)")
    op.execute("ALTER TABLE organization_invitations ADD CONSTRAINT organization_invitations_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE organization_users ADD CONSTRAINT organization_users_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE organization_users ADD CONSTRAINT organization_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE conversations ADD CONSTRAINT conversations_kb_id_fkey FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE conversations ADD CONSTRAINT conversations_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE conversations ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_kb_id_fkey FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_uploader_id_fkey FOREIGN KEY (uploader_id) REFERENCES users(id)")
    op.execute("ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_api_key_id_fkey FOREIGN KEY (api_key_id) REFERENCES api_keys(id)")
    op.execute("ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE chunks ADD CONSTRAINT chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE chunks ADD CONSTRAINT chunks_kb_id_fkey FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE chunks ADD CONSTRAINT chunks_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE messages ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE manager_profiles ADD CONSTRAINT manager_profiles_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE patient_profiles ADD CONSTRAINT patient_profiles_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE patient_family_links ADD CONSTRAINT patient_family_links_family_user_id_fkey FOREIGN KEY (family_user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE patient_family_links ADD CONSTRAINT patient_family_links_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES patient_profiles(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE patient_manager_assignments ADD CONSTRAINT patient_manager_assignments_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE management_suggestions ADD CONSTRAINT management_suggestions_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE audit_logs ADD CONSTRAINT audit_logs_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE audit_logs ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE roles ADD CONSTRAINT roles_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE role_permissions ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE role_permissions ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE organization_user_roles ADD CONSTRAINT organization_user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE management_suggestions ADD CONSTRAINT management_suggestions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES patient_profiles(id)")
    op.execute("ALTER TABLE management_suggestions ADD CONSTRAINT management_suggestions_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES users(id)")
    op.execute("ALTER TABLE manager_profiles ADD CONSTRAINT manager_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE patient_manager_assignments ADD CONSTRAINT patient_manager_assignments_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES patient_profiles(id)")
    op.execute("ALTER TABLE patient_manager_assignments ADD CONSTRAINT patient_manager_assignments_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES users(id)")
    op.execute("ALTER TABLE patient_profiles ADD CONSTRAINT patient_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES patient_profiles(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE messages ADD CONSTRAINT fk_messages_org_id FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE organization_user_roles ADD CONSTRAINT organization_user_roles_org_id_user_id_fkey FOREIGN KEY (org_id,user_id) REFERENCES organization_users(org_id,user_id) ON DELETE CASCADE")
    # --- Restore Policies ---
    op.execute("CREATE POLICY knowledge_bases_isolation_policy ON knowledge_bases USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY documents_isolation_policy ON documents USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY chunks_isolation_policy ON chunks USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY conversations_isolation_policy ON conversations USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY usage_logs_isolation_policy ON usage_logs USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY api_keys_isolation_policy ON api_keys USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY manager_profiles_isolation_policy ON manager_profiles USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY patient_manager_assignments_isolation_policy ON patient_manager_assignments USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY patient_profiles_isolation_policy ON patient_profiles USING ((org_id = current_setting('app.current_org_id')::bigint) OR (id IN ( SELECT patient_family_links.patient_id FROM patient_family_links WHERE ((patient_family_links.family_user_id = current_setting('app.current_user_id')::bigint) AND (patient_family_links.status = 'active')))))")
    op.execute("CREATE POLICY management_suggestions_isolation_policy ON management_suggestions USING ((org_id = current_setting('app.current_org_id')::bigint) OR (patient_id IN ( SELECT patient_family_links.patient_id FROM patient_family_links WHERE ((patient_family_links.family_user_id = current_setting('app.current_user_id')::bigint) AND (patient_family_links.status = 'active')))))")
    op.execute("CREATE POLICY audit_logs_isolation_policy ON audit_logs USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY messages_isolation_policy ON messages USING (org_id = current_setting('app.current_org_id')::bigint)")
    op.execute("CREATE POLICY organization_users_isolation_policy ON organization_users USING ((org_id = current_setting('app.current_org_id')::bigint) OR (user_id = current_setting('app.current_user_id')::bigint))")
    op.execute("CREATE POLICY patient_family_links_isolation_policy ON patient_family_links USING ((family_user_id = current_setting('app.current_user_id')::bigint) OR (patient_id IN ( SELECT patient_profiles.id FROM patient_profiles WHERE (patient_profiles.org_id = current_setting('app.current_org_id')::bigint))))")
    op.execute("CREATE POLICY organization_invitations_isolation_policy ON organization_invitations USING (org_id = current_setting('app.current_org_id')::bigint)")


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('usage_logs', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('usage_logs', 'resource_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=True)
    op.alter_column('usage_logs', 'api_key_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=True)
    op.alter_column('usage_logs', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=True)
    op.alter_column('usage_logs', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('roles', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('roles', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=True)
    op.add_column('role_permissions', sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.alter_column('role_permissions', 'permission_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('role_permissions', 'role_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('permissions', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_profiles', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_profiles', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_profiles', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_manager_assignments', 'patient_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_manager_assignments', 'manager_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_manager_assignments', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_family_links', 'access_level',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('patient_family_links', 'family_user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('patient_family_links', 'patient_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organizations', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_users', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_users', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_user_roles', 'role_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_user_roles', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_user_roles', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_invitations', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_invitations', 'inviter_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('organization_invitations', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('messages', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('messages', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('messages', 'conversation_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('manager_profiles', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('manager_profiles', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('manager_profiles', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('management_suggestions', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('management_suggestions', 'patient_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('management_suggestions', 'manager_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('management_suggestions', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('knowledge_bases', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('knowledge_bases', 'created_by',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('knowledge_bases', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('documents', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('documents', 'patient_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=True)
    op.alter_column('documents', 'uploader_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('documents', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('documents', 'kb_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('conversations', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('conversations', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('conversations', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('conversations', 'kb_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.drop_index('idx_chunk_tsv', table_name='chunks', postgresql_using='gin')
    op.alter_column('chunks', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('chunks', 'document_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('chunks', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('chunks', 'kb_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.drop_column('chunks', 'tsv_content')
    op.drop_column('chunks', 'metadata')
    op.alter_column('audit_logs', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('audit_logs', 'resource_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=True)
    op.alter_column('audit_logs', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('audit_logs', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=True)
    op.alter_column('api_keys', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('api_keys', 'created_by',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('api_keys', 'org_id',
               existing_type=sa.BigInteger(),
               type_=sa.UUID(),
               existing_nullable=False)
    # ### end Alembic commands ###
