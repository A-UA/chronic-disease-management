from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MenuRead(BaseModel):
    id: int
    name: str
    code: str
    menu_type: str
    path: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort: int = 0
    is_visible: bool = True
    is_enabled: bool = True
    meta: dict | None = None
    children: list[MenuRead] = []

    model_config = ConfigDict(from_attributes=True)
