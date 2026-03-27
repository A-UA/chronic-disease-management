from sqlalchemy import String, ForeignKey, Date, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from typing import TYPE_CHECKING
from .base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .organization import Organization


class PatientProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "patient_profiles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )

    real_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[Date | None] = mapped_column(Date)
    medical_history: Mapped[dict | None] = mapped_column(
        JSONB
    )  # Store diagnoses, allergies, etc.

    # Relationships
    user: Mapped["User"] = relationship()
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_patient_profiles_org_user"),
        Index(
            "idx_patient_medical_history_gin", "medical_history", postgresql_using="gin"
        ),
    )
