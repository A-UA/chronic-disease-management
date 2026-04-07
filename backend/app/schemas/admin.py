from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserAdminRead(BaseModel):
    id: int
    email: str
    name: str | None
    created_at: datetime
    org_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class OrganizationAdminRead(BaseModel):
    id: int
    name: str
    plan_type: str
    quota_tokens_limit: int
    quota_tokens_used: int
    member_count: int = 0
    patient_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenTrendItem(BaseModel):
    date: str
    tokens: int

class DashboardStats(BaseModel):
    total_organizations: int
    total_users: int
    active_users_24h: int
    total_patients: int
    total_conversations: int
    total_tokens_used: int
    token_usage_trend: list[TokenTrendItem]
    recent_failed_docs: int = 0


class UsageSummaryItem(BaseModel):
    org_id: int
    org_name: str
    total_tokens: int
    total_cost: float


class DynamicSettings(BaseModel):
    # Chat & RAG
    llm_default_model: str = "gpt-4o-mini"
    rag_max_chunks: int = 5
    rag_min_score: float = 0.0

    # System Status
    system_maintenance_mode: bool = False
    allow_new_registrations: bool = True

    # Quota
    default_org_token_quota: int = 1000000

    model_config = ConfigDict(from_attributes=True)


class SystemSettingRead(BaseModel):
    key: str
    value: str
    description: str | None = None


class SystemSettingUpdate(BaseModel):
    value: str
    description: str | None = None


class AuditLogRead(BaseModel):
    id: int
    user_id: int
    action: str
    resource_type: str
    resource_id: int | None = None
    details: str | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
