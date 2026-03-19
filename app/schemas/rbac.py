from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List

class PermissionRead(BaseModel):
    id: UUID
    name: str
    code: str
    description: str | None
    
    model_config = ConfigDict(from_attributes=True)

class RoleRead(BaseModel):
    id: UUID
    name: str
    code: str
    description: str | None
    is_system: bool
    permissions: List[PermissionRead]
    
    model_config = ConfigDict(from_attributes=True)

class RoleCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    permission_ids: List[UUID]
