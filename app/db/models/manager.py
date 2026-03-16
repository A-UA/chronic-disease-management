from sqlalchemy import String, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from .base import Base, UUIDMixin, TimestampMixin

class ManagerProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "manager_profiles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    
    title: Mapped[str | None] = mapped_column(String(100)) # Senior, Assistant, etc.
    bio: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user: Mapped["User"] = relationship()
    organization: Mapped["Organization"] = relationship()

class PatientManagerAssignment(Base, TimestampMixin):
    __tablename__ = "patient_manager_assignments"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    manager_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), primary_key=True)
    
    assignment_role: Mapped[str] = mapped_column(String(50), default='main') # main, assistant
    
    # Relationships
    manager: Mapped["User"] = relationship()
    patient: Mapped["PatientProfile"] = relationship()

class ManagementSuggestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "management_suggestions"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    manager_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(50), default='general') # clinical, lifestyle, medication
    
    # Relationships
    manager: Mapped["User"] = relationship()
    patient: Mapped["PatientProfile"] = relationship()
