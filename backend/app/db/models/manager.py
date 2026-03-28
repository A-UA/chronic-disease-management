from sqlalchemy import BigInteger, String, ForeignKey, Boolean, Text, Index, UniqueConstraint
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .organization import Organization
    from .patient import PatientProfile

class ManagerProfile(Base, IDMixin, TimestampMixin):
    __tablename__ = "manager_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    
    title: Mapped[str | None] = mapped_column(String(100)) # Senior, Assistant, etc.
    bio: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user: Mapped["User"] = relationship()
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_manager_profiles_org_user"),
    )

class PatientManagerAssignment(Base, TimestampMixin):
    __tablename__ = "patient_manager_assignments"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), primary_key=True)
    
    assignment_role: Mapped[str] = mapped_column(String(50), default='main') # main, assistant
    
    # Relationships
    manager: Mapped["User"] = relationship()
    patient: Mapped["PatientProfile"] = relationship()

class ManagementSuggestion(Base, IDMixin, TimestampMixin):
    __tablename__ = "management_suggestions"

    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id"), index=True)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(50), default='general') # clinical, lifestyle, medication
    
    # Relationships
    manager: Mapped["User"] = relationship()
    patient: Mapped["PatientProfile"] = relationship()

    __table_args__ = (
        Index('idx_org_patient_suggest', 'org_id', 'patient_id', 'created_at'),
    )
