from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime

class OrganizationBase(BaseModel):
    name: str
    plan_type: str = "free"

class OrganizationCreate(OrganizationBase):
    code: str = ""
    description: str | None = None

class OrganizationUpdate(BaseModel):
    name: str | None = None
    plan_type: str | None = None
    description: str | None = None
    status: str | None = None

class OrganizationReadPublic(BaseModel):
    """组织公开信息"""
    id: int
    name: str
    code: str = ""
    status: str = "active"
    plan_type: str = "free"
    tenant_id: int | None = None
    description: str | None = None
    sort: int = 0
    created_at: datetime | None = None
    
    model_config = ConfigDict(from_attributes=True)

class OrganizationReadAdmin(OrganizationReadPublic):
    """管理视图（含额外统计信息，按需填充）"""
    pass

class OrganizationMemberRead(BaseModel):
    user_id: int
    email: str
    name: str | None = None
    roles: list[str] = []
    user_type: str

class PatientAssignmentCreate(BaseModel):
    patient_id: int
    manager_id: int
    role: str = "main"

class OrganizationInvitationCreate(BaseModel):
    email: str
    role: str

from datetime import datetime

class OrganizationInvitationRead(BaseModel):
    id: int
    org_id: int
    inviter_id: int
    email: str
    role: str
    token: str
    status: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
