"""对话运行时入口服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class ChatRuntimeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def chat(self, *, request, current_user: User, tenant_id: int, org_id: int):
        """对话分发（Agent vs Standard）"""
        if request.use_agent:
            from app.services.agent.service import handle_agent_chat

            return await handle_agent_chat(
                request=request,
                db=self.db,
                tenant_id=tenant_id,
                org_id=org_id,
                current_user=current_user,
            )

        from app.services.rag.chat_service import handle_standard_chat

        return await handle_standard_chat(
            request=request,
            current_user=current_user,
            tenant_id=tenant_id,
            org_id=org_id,
            db=self.db,
        )
