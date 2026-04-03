from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional


class MenuRead(BaseModel):
    id: int
    name: str
    code: str
    menu_type: str
    path: Optional[str] = None
    icon: Optional[str] = None
    permission_code: Optional[str] = None
    sort: int = 0
    is_visible: bool = True
    is_enabled: bool = True
    meta: Optional[dict] = None
    children: list[MenuRead] = []

    model_config = ConfigDict(from_attributes=True)
