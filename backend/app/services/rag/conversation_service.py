"""对话管理业务服务"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ForbiddenError, NotFoundError
from app.models import Conversation, Message


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_conv(self, conv_id: int, user_id: int, tenant_id: int) -> Conversation:
        """获取并校验对话所有权"""
        conv = await self.db.get(Conversation, conv_id)
        if not conv:
            raise NotFoundError("Conversation", conv_id)
        if conv.user_id != user_id or conv.tenant_id != tenant_id:
            raise ForbiddenError("Not authorized")
        return conv

    async def list_conversations(
        self, user_id: int, tenant_id: int, skip: int = 0, limit: int = 50
    ) -> list[Conversation]:
        """列出用户对话"""
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.tenant_id == tenant_id)
            .order_by(Conversation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_conversation_detail(
        self, conv_id: int, user_id: int, tenant_id: int
    ) -> dict:
        """获取对话详情含消息"""
        conv = await self._get_conv(conv_id, user_id, tenant_id)
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        return {
            "id": conv.id, "kb_id": conv.kb_id, "title": conv.title,
            "created_at": conv.created_at, "messages": messages,
        }

    async def rename_conversation(
        self, conv_id: int, user_id: int, tenant_id: int, title: str
    ) -> Conversation:
        """重命名对话"""
        conv = await self._get_conv(conv_id, user_id, tenant_id)
        conv.title = title
        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def delete_conversation(
        self, conv_id: int, user_id: int, tenant_id: int
    ) -> None:
        """删除对话"""
        conv = await self._get_conv(conv_id, user_id, tenant_id)
        await self.db.delete(conv)
        await self.db.commit()
