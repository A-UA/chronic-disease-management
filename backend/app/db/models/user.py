from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from .base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from .organization import OrganizationUser

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationships
    organizations: Mapped[list["OrganizationUser"]] = relationship(back_populates="user")
