from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chat import retrieve_chunks


@pytest.mark.asyncio
async def test_retrieve_chunks_uses_normalized_query_for_embedding_and_cache():
    kb_id = uuid4()
    org_id = uuid4()
    raw_query = "  血糖高怎么办？\n\n"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    provider = MagicMock()
    provider.embed_query.return_value = [0.1] * 3

    with patch("app.services.chat.registry.get_embedding", return_value=provider), patch(
        "app.services.chat.redis_client.get",
        AsyncMock(return_value=None),
    ) as mock_cache_get, patch(
        "app.services.chat.redis_client.setex",
        AsyncMock(return_value=True),
    ):
        await retrieve_chunks(mock_db, raw_query, kb_id, org_id)

    provider.embed_query.assert_called_once_with("血糖高怎么办?")
    assert mock_cache_get.await_count == 1
