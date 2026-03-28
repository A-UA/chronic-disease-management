from pydantic import BaseModel, ConfigDict
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
    id: int
    user_id: int
    org_id: int
    
    model_config = ConfigDict(from_attributes=True)
