from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str | None = None

class UserCreate(UserBase):
    password: str

class UserRead(BaseModel):
    id: int
    email: str
    name: str | None = None
    created_at: datetime
    tenant_id: int | None = None
    org_id: int | None = None
    permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: str | None = None

class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str
