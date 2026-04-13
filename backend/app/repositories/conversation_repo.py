from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Conversation)

    async def list_by_user(self, user_id: int, tenant_id: int, skip: int = 0, limit: int = 50) -> list[Conversation]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id, self.model.tenant_id == tenant_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_all(self, tenant_id: int, effective_org_id: int | None, skip: int = 0, limit: int = 50) -> list[Conversation]:
        stmt = select(self.model).where(self.model.tenant_id == tenant_id)
        if effective_org_id is not None:
            stmt = stmt.where(self.model.org_id == effective_org_id)
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_with_messages(self, conv_id: int, tenant_id: int) -> Conversation | None:
        stmt = (
            select(self.model)
            .options(selectinload(self.model.messages))
            .where(self.model.id == conv_id, self.model.tenant_id == tenant_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Message)
