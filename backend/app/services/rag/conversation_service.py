"""对话管理业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ForbiddenError, NotFoundError
from app.models import Conversation
from app.repositories.conversation_repo import ConversationRepository


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ConversationRepository(db)

    async def list_conversations(
        self, user_id: int, tenant_id: int, skip: int = 0, limit: int = 50
    ) -> list[Conversation]:
        """列出用户个人对话"""
        return await self.repo.list_by_user(user_id=user_id, tenant_id=tenant_id, skip=skip, limit=limit)

    async def list_all_conversations(
        self, tenant_id: int, effective_org_id: int | None, skip: int = 0, limit: int = 50
    ) -> list[Conversation]:
        """[管理员] 平台/组织全局对话"""
        return await self.repo.list_all(tenant_id=tenant_id, effective_org_id=effective_org_id, skip=skip, limit=limit)

    async def get_conversation_detail(
        self, conv_id: int, user_id: int, tenant_id: int
    ) -> dict:
        """获取对话详情与消息列表"""
        conv = await self.repo.get_with_messages(conv_id, tenant_id)
        if not conv:
            raise NotFoundError("Conversation", conv_id)
        if conv.user_id != user_id:
            raise ForbiddenError("You can only access your own conversations")

        return {
            "id": conv.id,
            "kb_id": conv.kb_id,
            "title": conv.title,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "citations": m.citations,
                    "created_at": m.created_at,
                }
                for m in conv.messages
            ],
        }

    async def delete_conversation(
        self, conv_id: int, user_id: int, tenant_id: int
    ) -> None:
        """删除个人对话"""
        conv = await self.repo.get_by_id(conv_id)
        if not conv or conv.tenant_id != tenant_id:
            raise NotFoundError("Conversation", conv_id)
        if conv.user_id != user_id:
            raise ForbiddenError("You can only delete your own conversations")

        await self.repo.delete(conv)
        await self.db.commit()
