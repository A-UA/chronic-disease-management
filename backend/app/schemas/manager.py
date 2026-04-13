"""管理师 Schema/DTO"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ManagerDetailRead(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    email: str | None = None
    title: str | None = None
    is_active: bool
    assigned_patient_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class PatientBriefRead(BaseModel):
    id: int
    user_id: int
    real_name: str
    gender: str | None = None
    model_config = ConfigDict(from_attributes=True)


class SuggestionCreate(BaseModel):
    content: str
    suggestion_type: str = "general"


class SuggestionRead(BaseModel):
    id: int
    manager_id: int
    patient_id: int
    content: str
    suggestion_type: str
    created_at: Any
    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    patient_id: int
    manager_id: int
    assignment_role: str = "main"


class ManagerProfileCreate(BaseModel):
    user_id: int
    title: str | None = None
    bio: str | None = None


class ManagerProfileUpdate(BaseModel):
    title: str | None = None
    bio: str | None = None
    is_active: bool | None = None


class SuggestionUpdate(BaseModel):
    content: str | None = None
    suggestion_type: str | None = None
