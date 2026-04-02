from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ApiKeyCreate(BaseModel):
    name: str
    qps_limit: int | None = 10
    token_quota: int | None = None
    expires_at: datetime | None = None

class ApiKeyUpdate(BaseModel):
    name: str | None = None
    qps_limit: int | None = None
    token_quota: int | None = None
    status: str | None = None
    expires_at: datetime | None = None

class ApiKeyRead(BaseModel):
    id: int
    org_id: int
    created_by: int
    name: str
    key_prefix: str
    qps_limit: int
    token_quota: int | None
    token_used: int
    status: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApiKeyCreateResponse(ApiKeyRead):
    raw_key: str
