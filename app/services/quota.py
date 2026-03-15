import time
import redis
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.config import settings
from app.db.models import Organization, ApiKey

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def check_org_quota(db: AsyncSession, org_id: UUID) -> Organization:
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    if org.quota_tokens_used >= org.quota_tokens_limit:
        raise HTTPException(status_code=402, detail="Organization token quota exceeded. Please upgrade your plan.")
        
    return org

def check_api_key_rate_limit(api_key_id: UUID, qps_limit: int):
    # Simple Token Bucket or Fixed Window via Redis
    key = f"rate_limit:api_key:{api_key_id}"
    current_time = int(time.time())
    window_key = f"{key}:{current_time}"
    
    # Increment counter for the current second
    requests = redis_client.incr(window_key)
    if requests == 1:
        redis_client.expire(window_key, 5) # Expire in 5 seconds
        
    if requests > qps_limit:
        raise HTTPException(status_code=429, detail="Too Many Requests")
