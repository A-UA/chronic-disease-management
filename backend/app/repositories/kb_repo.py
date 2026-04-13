from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models import KnowledgeBase, Document, Chunk
from app.repositories.base import BaseRepository

class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, KnowledgeBase)
        
    async def list_by_tenant(self, tenant_id: int, effective_org_id: int | None, search: str | None = None, skip: int = 0, limit: int = 50) -> tuple[int, list[KnowledgeBase]]:
        base = select(self.model).where(self.model.tenant_id == tenant_id)
        if effective_org_id is not None:
            base = base.where(self.model.org_id == effective_org_id)
        if search:
            base = base.where(self.model.name.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = base.offset(skip).limit(limit).order_by(self.model.created_at.desc())
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Document)

    async def count_by_kb(self, kb_id: int) -> int:
        stmt = select(func.count(self.model.id)).where(self.model.kb_id == kb_id)
        return (await self.db.execute(stmt)).scalar() or 0

class ChunkRepository(BaseRepository[Chunk]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Chunk)
        
    async def get_token_count_by_kb(self, kb_id: int) -> int:
        stmt = (
            select(func.sum(self.model.token_count))
            .join(Document, self.model.document_id == Document.id)
            .where(Document.kb_id == kb_id, self.model.deleted_at.is_(None))
        )
        return (await self.db.execute(stmt)).scalar() or 0
