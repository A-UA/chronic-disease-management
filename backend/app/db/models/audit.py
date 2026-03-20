from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from .base import Base, UUIDMixin, TimestampMixin

class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    org_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    action: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "view_patient", "update_patient", "chat"
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "PatientProfile", "Conversation"
    resource_id: Mapped[UUID | None] = mapped_column(index=True)
    
    details: Mapped[str | None] = mapped_column(Text) # JSON string or plain text describing the change
    ip_address: Mapped[str | None] = mapped_column(String(45))
