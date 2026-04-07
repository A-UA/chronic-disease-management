import time

import redis.asyncio as redis
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Tenant

_redis_client = None


class _RedisClientProxy:
    def __getattr__(self, item):
        return getattr(get_redis_client(), item)


redis_client = _RedisClientProxy()


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=settings.REDIS_POOL_SIZE,
        )
    return _redis_client


async def check_tenant_quota(db: AsyncSession, tenant_id: int) -> Tenant:
    """校验租户级 Token 配额"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.quota_tokens_used >= tenant.quota_tokens_limit:
        raise HTTPException(
            status_code=402,
            detail="Tenant token quota exceeded. Please upgrade your plan.",
        )

    quota_key = f"quota:tenant:{tenant_id}"
    await get_redis_client().set(
        quota_key, tenant.quota_tokens_limit - tenant.quota_tokens_used, ex=300
    )
    return tenant


# 保留旧函数名作为兼容别名
async def check_org_quota(db: AsyncSession, org_id: int) -> Tenant:
    """向后兼容：通过 org_id 查找对应租户的配额"""
    from app.db.models import Organization
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return await check_tenant_quota(db, org.tenant_id)


async def check_quota_during_stream(
    tenant_id: int, tokens_so_far: int, db: AsyncSession | None = None
) -> bool:
    """流式响应中的实时配额检查"""
    quota_key = f"quota:tenant:{tenant_id}"
    remaining = await get_redis_client().get(quota_key)
    if remaining is None:
        if db is None:
            return True
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            return False
        remaining_tokens = tenant.quota_tokens_limit - tenant.quota_tokens_used
        return remaining_tokens > tokens_so_far

    return int(remaining) > tokens_so_far


async def check_api_key_rate_limit(api_key_id: int, qps_limit: int):
    key = f"rate_limit:api_key:{api_key_id}"
    current_time = int(time.time())
    window_key = f"{key}:{current_time}"

    rc = get_redis_client()
    requests = await rc.incr(window_key)
    if requests == 1:
        await rc.expire(window_key, 5)

    if requests > qps_limit:
        raise HTTPException(status_code=429, detail="Too Many Requests")


async def update_tenant_quota(db: AsyncSession, tenant_id: int, tokens_consumed: int):
    """更新租户 Token 消耗量"""
    from sqlalchemy import update

    stmt = (
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(quota_tokens_used=Tenant.quota_tokens_used + tokens_consumed)
    )
    await db.execute(stmt)


# 保留旧函数名作为兼容别名
async def update_org_quota(db: AsyncSession, org_id: int, tokens_consumed: int):
    from app.db.models import Organization
    org = await db.get(Organization, org_id)
    if org:
        await update_tenant_quota(db, org.tenant_id, tokens_consumed)
