from sqlalchemy import String, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from uuid import UUID
from .base import Base, UUIDMixin, TimestampMixin
from .user import User
from .organization import Organization

class KnowledgeBase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_bases"

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    kb_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    uploader_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    minio_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='processing', server_default='processing')

class Chunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chunks"

    kb_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # 1536 is standard for text-embedding-3-small and ada-002
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)

    __table_args__ = (
        Index('idx_org_kb_chunk', 'org_id', 'kb_id'),
    )
