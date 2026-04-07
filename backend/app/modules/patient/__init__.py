"""Patient module - PatientProfile, HealthMetric, Manager, Family"""
# Models
from app.db.models.patient import PatientProfile  # noqa: F401
from app.db.models.health_metric import HealthMetric  # noqa: F401
from app.db.models.manager import (  # noqa: F401
    ManagerProfile, PatientManagerAssignment, ManagementSuggestion,
)
from app.db.models.organization import PatientFamilyLink  # noqa: F401

# Schemas (import on demand to avoid missing optional schemas)
# from app.schemas.patient import PatientCreate, PatientRead
# from app.schemas.health_metric import HealthMetricCreate, HealthMetricRead
