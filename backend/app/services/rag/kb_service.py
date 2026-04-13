"""知识库管理业务服务"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ForbiddenError, NotFoundError
from app.models import Chunk, Document, KnowledgeBase


class KBService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_kb(
        self, *, tenant_id: int, org_id: int, created_by: int, name: str, description: str | None
    ) -> dict:
        """创建知识库"""
        kb = KnowledgeBase(
            tenant_id=tenant_id, org_id=org_id, created_by=created_by, name=name, description=description
        )
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        return {
            "id": kb.id, "name": kb.name, "description": kb.description,
            "org_id": kb.org_id, "document_count": 0, "chunk_count": 0, "created_at": kb.created_at,
        }

    async def list_kbs(
        self, tenant_id: int, org_id: int | None = None, skip: int = 0, limit: int = 100
    ) -> list[dict]:
        """列出知识库（含聚合统计）"""
        doc_count_sq = (
            select(Document.kb_id, func.count(Document.id).label("document_count"))
            .where(Document.deleted_at.is_(None))
            .group_by(Document.kb_id)
            .subquery()
        )
        chunk_count_sq = (
            select(Chunk.kb_id, func.count(Chunk.id).label("chunk_count"))
            .where(Chunk.deleted_at.is_(None))
            .group_by(Chunk.kb_id)
            .subquery()
        )

        stmt = (
            select(
                KnowledgeBase,
                func.coalesce(doc_count_sq.c.document_count, 0).label("document_count"),
                func.coalesce(chunk_count_sq.c.chunk_count, 0).label("chunk_count"),
            )
            .outerjoin(doc_count_sq, KnowledgeBase.id == doc_count_sq.c.kb_id)
            .outerjoin(chunk_count_sq, KnowledgeBase.id == chunk_count_sq.c.kb_id)
            .where(KnowledgeBase.tenant_id == tenant_id)
        )
        if org_id is not None:
            stmt = stmt.where(KnowledgeBase.org_id == org_id)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return [
            {
                "id": kb.id, "name": kb.name, "description": kb.description,
                "org_id": kb.org_id, "document_count": doc_cnt,
                "chunk_count": chunk_cnt, "created_at": kb.created_at,
            }
            for kb, doc_cnt, chunk_cnt in result.all()
        ]

    async def _get_kb(self, kb_id: int, tenant_id: int, org_id: int | None) -> KnowledgeBase:
        """获取并校验知识库"""
        kb = await self.db.get(KnowledgeBase, kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise NotFoundError("Knowledge base", kb_id)
        if org_id is not None and kb.org_id != org_id:
            raise ForbiddenError("Not enough permissions")
        return kb

    async def update_kb(
        self, kb_id: int, tenant_id: int, org_id: int | None, data: dict
    ) -> dict:
        """更新知识库"""
        kb = await self._get_kb(kb_id, tenant_id, org_id)
        for field, value in data.items():
            setattr(kb, field, value)
        await self.db.commit()
        await self.db.refresh(kb)

        doc_count = (await self.db.execute(
            select(func.count(Document.id)).where(Document.kb_id == kb_id, Document.deleted_at.is_(None))
        )).scalar() or 0
        chunk_count = (await self.db.execute(
            select(func.count(Chunk.id)).where(Chunk.kb_id == kb_id, Chunk.deleted_at.is_(None))
        )).scalar() or 0

        return {
            "id": kb.id, "name": kb.name, "description": kb.description,
            "org_id": kb.org_id, "document_count": doc_count,
            "chunk_count": chunk_count, "created_at": kb.created_at,
        }

    async def delete_kb(self, kb_id: int, tenant_id: int, org_id: int | None) -> None:
        """删除知识库"""
        kb = await self._get_kb(kb_id, tenant_id, org_id)
        await self.db.delete(kb)
        await self.db.commit()

    async def get_kb_stats(self, kb_id: int, tenant_id: int, org_id: int | None) -> dict:
        """知识库统计"""
        kb = await self._get_kb(kb_id, tenant_id, org_id)
        doc_count = (await self.db.execute(
            select(func.count(Document.id)).where(Document.kb_id == kb_id)
        )).scalar() or 0
        chunk_count = (await self.db.execute(
            select(func.count(Chunk.id)).where(Chunk.kb_id == kb_id)
        )).scalar() or 0
        total_tokens = (await self.db.execute(
            select(func.coalesce(func.sum(Chunk.metadata_["token_count"].as_integer()), 0)).where(Chunk.kb_id == kb_id)
        )).scalar() or 0
        return {"kb_id": kb_id, "document_count": doc_count, "chunk_count": chunk_count, "total_tokens": total_tokens}
