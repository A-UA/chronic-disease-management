from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class UserAdminRead(BaseModel):
    id: UUID
    email: str
    name: str | None
    created_at: datetime
    org_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class OrganizationAdminRead(BaseModel):
    id: UUID
    name: str
    plan_type: str
    quota_tokens_limit: int
    quota_tokens_used: int
    member_count: int = 0
    patient_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_organizations: int
    total_users: int
    total_patients: int
    total_conversations: int
    total_tokens_used: int


class UsageSummaryItem(BaseModel):
    org_id: UUID
    org_name: str
    total_tokens: int
    total_cost: float


class SystemSettingRead(BaseModel):
    key: str
    value: str
    description: str | None = None


class SystemSettingUpdate(BaseModel):
    value: str
    description: str | None = None


class AuditLogRead(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID | None = None
    details: str | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    id: UUID
    user_id: UUID
    title: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
