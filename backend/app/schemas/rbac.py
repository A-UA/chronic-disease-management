from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any

class PermissionRead(BaseModel):
    id: int
    name: str
    code: str
    permission_type: str
    ui_metadata: Optional[dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)

class MenuRead(BaseModel):
    id: int
    name: str
    code: str
    path: str
    icon: Optional[str] = None
    sort: int = 100
    
    model_config = ConfigDict(from_attributes=True)

class RoleRead(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool
    parent_role_id: Optional[int] = None
    permissions: List[PermissionRead]
    
    model_config = ConfigDict(from_attributes=True)

class RoleCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    parent_role_id: Optional[int] = None
    permission_ids: List[int]
