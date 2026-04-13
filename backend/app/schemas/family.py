"""家属关联 Schema/DTO"""

from datetime import date

from pydantic import BaseModel, ConfigDict


class FamilyLinkCreate(BaseModel):
    patient_id: int
    family_user_email: str
    relationship_type: str | None = None
    access_level: int = 1


class FamilyLinkRead(BaseModel):
    patient_id: int
    family_user_id: int
    relationship_type: str | None
    access_level: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class PatientProfileFamilyRead(BaseModel):
    id: int
    real_name: str
    gender: str | None
    birth_date: date | None
    medical_history: dict | None
    relationship_type: str | None

    model_config = ConfigDict(from_attributes=True)
