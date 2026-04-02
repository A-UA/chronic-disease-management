from pydantic import BaseModel, ConfigDict, computed_field

class OrganizationBase(BaseModel):
    name: str
    plan_type: str = "free"

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: str | None = None
    plan_type: str | None = None
    quota_tokens_limit: int | None = None

class OrganizationReadPublic(OrganizationBase):
    """Viewable by any member or patient."""
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class OrganizationReadAdmin(OrganizationReadPublic):
    """Viewable only by organization admins."""
    quota_tokens_limit: int
    quota_tokens_used: int

    @computed_field
    def quota_usage_percent(self) -> float:
        if self.quota_tokens_limit == 0:
            return 0.0
        return round((self.quota_tokens_used / self.quota_tokens_limit) * 100, 2)

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
