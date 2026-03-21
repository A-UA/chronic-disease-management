import time
from uuid import UUID

import redis.asyncio as redis
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ApiKey, Organization

_redis_client = None


class _RedisClientProxy:
    def __getattr__(self, item):
        return getattr(get_redis_client(), item)


redis_client = _RedisClientProxy()


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def check_org_quota(db: AsyncSession, org_id: UUID) -> Organization:
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org.quota_tokens_used >= org.quota_tokens_limit:
        raise HTTPException(status_code=402, detail="Organization token quota exceeded. Please upgrade your plan.")

    quota_key = f"quota:org:{org_id}"
    await get_redis_client().set(quota_key, org.quota_tokens_limit - org.quota_tokens_used, ex=300)
    return org


async def check_quota_during_stream(org_id: UUID, tokens_so_far: int, db: AsyncSession | None = None) -> bool:
    quota_key = f"quota:org:{org_id}"
    remaining = await get_redis_client().get(quota_key)
    if remaining is None:
        if db is None:
            return True
        org = await db.get(Organization, org_id)
        if org is None:
            return False
        remaining_tokens = org.quota_tokens_limit - org.quota_tokens_used
        return remaining_tokens > tokens_so_far

    return int(remaining) > tokens_so_far


async def check_api_key_rate_limit(api_key_id: UUID, qps_limit: int):
    key = f"rate_limit:api_key:{api_key_id}"
    current_time = int(time.time())
    window_key = f"{key}:{current_time}"

    redis_client = get_redis_client()
    requests = await redis_client.incr(window_key)
    if requests == 1:
        await redis_client.expire(window_key, 5)

    if requests > qps_limit:
        raise HTTPException(status_code=429, detail="Too Many Requests")


async def update_org_quota(db: AsyncSession, org_id: UUID, tokens_consumed: int):
    from sqlalchemy import update

    stmt = (
        update(Organization)
        .where(Organization.id == org_id)
        .values(quota_tokens_used=Organization.quota_tokens_used + tokens_consumed)
    )
    await db.execute(stmt)
    await db.commit()
