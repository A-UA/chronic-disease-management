"""API Key 业务服务"""

import hashlib
import hmac
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.config import settings
from app.base.exceptions import NotFoundError
from app.models import ApiKey
from app.repositories.api_key_repo import ApiKeyRepository


class ApiKeyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ApiKeyRepository(db)

    async def create_api_key(self, *, tenant_id: int, org_id: int, user_id: int, data: dict) -> dict:
        """创建 API Key"""
        raw_key = secrets.token_urlsafe(32)
        key_prefix = raw_key[:8]
        key_hash = hmac.new(
            settings.API_KEY_SALT.encode(), raw_key.encode(), hashlib.sha256
        ).hexdigest()

        qps_limit = data.get("qps_limit", 10)
        if qps_limit is None:
            qps_limit = 10

        api_key = ApiKey(
            tenant_id=tenant_id,
            org_id=org_id,
            created_by=user_id,
            name=data["name"],
            key_prefix=key_prefix,
            key_hash=key_hash,
            qps_limit=qps_limit,
            token_quota=data.get("token_quota"),
            expires_at=data.get("expires_at"),
        )
        
        await self.repo.create(api_key)
        await self.db.commit()

        return {
            "id": api_key.id, "org_id": api_key.org_id, "created_by": api_key.created_by,
            "name": api_key.name, "key_prefix": api_key.key_prefix, "qps_limit": api_key.qps_limit,
            "token_quota": api_key.token_quota, "token_used": api_key.token_used,
            "status": api_key.status, "expires_at": api_key.expires_at,
            "created_at": api_key.created_at, "updated_at": api_key.updated_at,
            "raw_key": raw_key,
        }

    async def list_api_keys(self, org_id: int, skip: int = 0, limit: int = 50) -> list[ApiKey]:
        """列出组织的 API Key"""
        return await self.repo.list_by_org(org_id=org_id, skip=skip, limit=limit)

    async def update_api_key(self, api_key_id: int, org_id: int, data: dict) -> ApiKey:
        """更新 API Key"""
        api_key = await self.repo.get_by_id(api_key_id)
        if not api_key or api_key.org_id != org_id:
            raise NotFoundError("API Key", api_key_id)

        await self.repo.update(api_key, data)
        await self.db.commit()
        return api_key

    async def revoke_api_key(self, api_key_id: int, org_id: int) -> ApiKey:
        """吊销 API Key"""
        api_key = await self.repo.get_by_id(api_key_id)
        if not api_key or api_key.org_id != org_id:
            raise NotFoundError("API Key", api_key_id)

        await self.repo.update(api_key, {"status": "revoked"})
        await self.db.commit()
        return api_key
