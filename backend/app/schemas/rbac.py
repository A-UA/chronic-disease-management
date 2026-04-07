from typing import Any

from pydantic import BaseModel, ConfigDict


class PermissionRead(BaseModel):
    id: int
    name: str
    code: str
    permission_type: str
    ui_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

class MenuRead(BaseModel):
    id: int
    name: str
    code: str
    path: str
    icon: str | None = None
    sort: int = 100

    model_config = ConfigDict(from_attributes=True)

class RoleRead(BaseModel):
    id: int
    name: str
    code: str
    description: str | None = None
    is_system: bool
    parent_role_id: int | None = None
    permissions: list[PermissionRead]

    model_config = ConfigDict(from_attributes=True)

class RoleCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    parent_role_id: int | None = None
    permission_ids: list[int]
