from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import List, Optional

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRead(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    created_at: datetime
    tenant_id: Optional[int] = None
    org_id: Optional[int] = None
    permissions: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str
