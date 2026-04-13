"""知识库管理业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import NotFoundError
from app.models import KnowledgeBase
from app.repositories.kb_repo import ChunkRepository, DocumentRepository, KnowledgeBaseRepository


class KBService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = KnowledgeBaseRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)

    async def _kb_read(self, kb: KnowledgeBase) -> dict:
        """构建知识库视图 (带统计指标)"""
        doc_count = await self.doc_repo.count_by_kb(kb.id)
        token_count = await self.chunk_repo.get_token_count_by_kb(kb.id)
        
        return {
            "id": kb.id,
            "tenant_id": kb.tenant_id,
            "org_id": kb.org_id,
            "name": kb.name,
            "description": kb.description,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
            "document_count": doc_count,
            "token_count": token_count,
        }

    async def list_kbs(
        self,
        tenant_id: int,
        effective_org_id: int | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """列出知识库"""
        total, kbs = await self.repo.list_by_tenant(
            tenant_id=tenant_id, effective_org_id=effective_org_id, search=search, skip=skip, limit=limit
        )

        kb_reads = [await self._kb_read(kb) for kb in kbs]
        return {"total": total, "items": kb_reads}

    async def get_kb(self, kb_id: int, tenant_id: int) -> dict:
        """获取知识库详情"""
        kb = await self.repo.get_by_id(kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise NotFoundError("Knowledge base", kb_id)
        return await self._kb_read(kb)

    async def create_kb(
        self, tenant_id: int, org_id: int, data: dict, created_by: int = 0
    ) -> dict:
        """创建知识库"""
        kb = KnowledgeBase(tenant_id=tenant_id, org_id=org_id, created_by=created_by, **data)
        await self.repo.create(kb)
        await self.db.commit()
        return await self._kb_read(kb)

    async def update_kb(
        self, kb_id: int, tenant_id: int, data: dict
    ) -> dict:
        """更新知识库"""
        kb = await self.repo.get_by_id(kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise NotFoundError("Knowledge base", kb_id)

        await self.repo.update(kb, data)
        await self.db.commit()
        return await self._kb_read(kb)

    async def delete_kb(self, kb_id: int, tenant_id: int) -> None:
        """删除知识库"""
        kb = await self.repo.get_by_id(kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise NotFoundError("Knowledge base", kb_id)

        # 关联的 documents 会通过 DB 外键或者应用侧的清理任务被删
        await self.repo.delete(kb)
        await self.db.commit()
