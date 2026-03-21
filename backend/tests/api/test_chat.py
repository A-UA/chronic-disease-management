import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_org, get_current_user, get_db, verify_quota
from app.api.endpoints.biz.chat import router


app = FastAPI()
app.include_router(router, prefix="/api/v1")


class DummyUser:
    def __init__(self):
        self.id = uuid4()


class DummyDB:
    def __init__(self):
        self.objects = {}
        self.added = []
        self.commits = 0

    async def get(self, model, obj_id):
        return self.objects.get(obj_id)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is not None:
            self.objects[obj.id] = obj

    async def commit(self):
        self.commits += 1


dummy_db = DummyDB()
current_org = uuid4()
current_user = DummyUser()


async def override_get_db():
    yield dummy_db


async def override_get_current_user():
    return current_user


async def override_get_current_org():
    return current_org


async def override_verify_quota():
    return None


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_current_org] = override_get_current_org
app.dependency_overrides[verify_quota] = override_verify_quota


@pytest.mark.asyncio
async def test_chat_stream_forwards_filters_and_streams_events(monkeypatch):
    dummy_db.objects = {}
    dummy_db.added = []
    dummy_db.commits = 0

    document_id = uuid4()
    conversation_id = uuid4()
    kb_id = uuid4()

    fake_chunk = MagicMock()
    fake_chunk.document_id = document_id
    fake_chunk.page_number = 2
    fake_chunk.content = "诊断：血糖升高。"

    retrieve_chunks = AsyncMock(return_value=[fake_chunk])
    monkeypatch.setattr("app.api.endpoints.biz.chat.retrieve_chunks", retrieve_chunks)
    monkeypatch.setattr(
        "app.api.endpoints.biz.chat.build_rag_prompt",
        lambda query, chunks: ("prompt-text", [{"doc_id": str(document_id), "ref": "Doc 1", "page": 2}]),
    )

    provider = MagicMock()

    async def stream_text(prompt: str):
        for token in ["Conclusion: 建议复查。", "\nEvidence: 两周后复查。"]:
            yield token

    provider.stream_text = stream_text
    provider.complete_text = AsyncMock(
        return_value='{"statements":[{"text":"Conclusion: 建议复查。","refs":["Doc 1"]},{"text":"Evidence: 两周后复查。","refs":["Doc 1"]}]}'
    )
    monkeypatch.setattr("app.api.endpoints.biz.chat.get_llm_provider", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.biz.chat.check_quota_during_stream", AsyncMock(return_value=True))
    monkeypatch.setattr("app.api.endpoints.biz.chat.update_org_quota", AsyncMock(return_value=None))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1",
            json={
                "kb_id": str(kb_id),
                "conversation_id": str(conversation_id),
                "query": "血糖高怎么办？",
                "document_ids": [str(document_id)],
                "file_types": ["pdf"],
            },
        )

    assert response.status_code == 200
    body = response.text
    assert "event: meta" in body
    assert "event: chunk" in body
    assert "event: done" in body
    assert "\\u5efa\\u8bae\\u590d\\u67e5" in body
    assert "statement_citations" in body

    retrieve_chunks.assert_awaited_once()
    _, called_query, called_kb_id, called_org_id = retrieve_chunks.await_args.args[:4]
    called_filters = retrieve_chunks.await_args.kwargs["filters"]
    assert called_query == "血糖高怎么办?"
    assert called_kb_id == kb_id
    assert called_org_id == current_org
    assert called_filters == {"document_ids": [document_id], "file_types": ["pdf"]}

    assistant_message = dummy_db.added[-2]
    usage_log = dummy_db.added[-1]
    assert assistant_message.metadata_["citations"][0]["page"] == 2
    assert assistant_message.metadata_["statement_citations"][0]["citations"][0]["doc_id"] == str(document_id)
    assert assistant_message.metadata_["observability"]["raw_query"] == "血糖高怎么办？"
    assert assistant_message.metadata_["observability"]["retrieval_query"] == "血糖高怎么办?"
    assert assistant_message.metadata_["observability"]["retrieved_chunk_count"] == 1
    assert usage_log.model == provider.model_name
