from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from app.services.quota import check_quota_during_stream


@pytest.mark.asyncio
async def test_check_quota_during_stream_falls_back_to_db_when_cache_missing_and_blocks():
    org_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(quota_tokens_limit=100, quota_tokens_used=95)

    with patch("app.services.quota.get_redis_client") as get_redis_client:
        redis_client = AsyncMock()
        redis_client.get.return_value = None
        get_redis_client.return_value = redis_client

        allowed = await check_quota_during_stream(org_id, tokens_so_far=10, db=db)

    assert allowed is False


@pytest.mark.asyncio
async def test_check_quota_during_stream_falls_back_to_db_when_cache_missing_and_allows():
    org_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(quota_tokens_limit=100, quota_tokens_used=20)

    with patch("app.services.quota.get_redis_client") as get_redis_client:
        redis_client = AsyncMock()
        redis_client.get.return_value = None
        get_redis_client.return_value = redis_client

        allowed = await check_quota_during_stream(org_id, tokens_so_far=10, db=db)

    assert allowed is True
