"""健康指标 Schema/DTO"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ALLOWED_METRIC_TYPES = {
    "blood_pressure",
    "blood_sugar",
    "weight",
    "heart_rate",
    "bmi",
    "spo2",
}


class HealthMetricCreate(BaseModel):
    metric_type: Literal[
        "blood_pressure", "blood_sugar", "weight", "heart_rate", "bmi", "spo2"
    ]
    value: float
    value_secondary: float | None = None
    unit: str
    measured_at: datetime
    note: str | None = None


class HealthMetricRead(BaseModel):
    id: int
    patient_id: int
    metric_type: str
    value: float
    value_secondary: float | None
    unit: str
    measured_at: datetime
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthMetricUpdate(BaseModel):
    value: float | None = None
    value_secondary: float | None = None
    unit: str | None = None
    note: str | None = None
