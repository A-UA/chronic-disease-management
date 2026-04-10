from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .organization import Organization
    from .user import User


class PatientProfile(Base, IDMixin, TimestampMixin):
    __tablename__ = "patient_profiles"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )

    real_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[Date | None] = mapped_column(Date)
    medical_history: Mapped[dict | None] = mapped_column(
        JSONB,
    )  # Store diagnoses, allergies, etc.

    # Relationships
    user: Mapped["User"] = relationship()
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "org_id", "user_id", name="uq_patient_profiles_tenant_org_user"
        ),
        Index(
            "idx_patient_medical_history_gin", "medical_history", postgresql_using="gin"
        ),
        Index("idx_patient_profiles_tenant_org", "tenant_id", "org_id"),
    )
