from sqlalchemy import BigInteger, String, ForeignKey, Text
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, IDMixin, TimestampMixin

class AuditLog(Base, IDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    action: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "view_patient", "update_patient", "chat"
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "PatientProfile", "Conversation"
    resource_id: Mapped[int | None] = mapped_column(index=True)
    
    details: Mapped[str | None] = mapped_column(Text) # JSON string or plain text describing the change
    ip_address: Mapped[str | None] = mapped_column(String(45))
