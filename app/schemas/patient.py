from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date

class PatientProfileBase(BaseModel):
    real_name: str
    gender: str | None = None
    birth_date: date | None = None
    medical_history: dict | None = None

class PatientProfileCreate(PatientProfileBase):
    pass

class PatientProfileUpdate(BaseModel):
    real_name: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    medical_history: dict | None = None

class PatientProfileRead(PatientProfileBase):
    id: UUID
    user_id: UUID
    org_id: UUID
    
    model_config = ConfigDict(from_attributes=True)
