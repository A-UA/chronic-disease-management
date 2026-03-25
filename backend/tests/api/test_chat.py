"""Chat API endpoint 集成测试"""
import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_org, get_current_user, get_db, verify_quota
from app.api.endpoints.biz.chat import router
from app.db.models import Conversation, KnowledgeBase


app = FastAPI()
app.include_router(router, prefix="/api/v1")


class DummyUser:
    def __init__(self):
        self.id = uuid4()


class DummyScalars:
    def all(self):
        return []


class DummyExecResult:
    def scalars(self):
        return DummyScalars()


class DummyDB:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.objects = {}

    async def get(self, model, obj_id):
        return self.objects.get((model, obj_id))

    async def execute(self, stmt, *args, **kwargs):
        return DummyExecResult()

    async def refresh(self, obj):
        pass

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


dummy_db = DummyDB()
current_org = uuid4()
current_user = DummyUser()

app.dependency_overrides[get_db] = lambda: _override_db()
app.dependency_overrides[get_current_user] = lambda: current_user
app.dependency_overrides[get_current_org] = lambda: current_org
app.dependency_overrides[verify_quota] = lambda: None


async def _override_db():
    yield dummy_db


app.dependency_overrides[get_db] = _override_db


@pytest.mark.asyncio
async def test_chat_stream_full_flow(monkeypatch):
    dummy_db.added.clear()
    dummy_db.commits = 0
    dummy_db.objects = {}
    kb_id = uuid4()

    doc_id = uuid4()
    fake_chunk = MagicMock()
    fake_chunk.document_id = doc_id
    fake_chunk.page_number = 2
    fake_chunk.content = "诊断：血糖升高。"

    monkeypatch.setattr(
        "app.api.endpoints.biz.chat.retrieve_chunks",
        AsyncMock(return_value=[fake_chunk]),
    )
    monkeypatch.setattr(
        "app.api.endpoints.biz.chat.build_rag_prompt",
        lambda q, c: ("prompt", [{"doc_id": str(doc_id), "ref": "Doc 1", "page": 2,
                                   "chunk_id": "c1", "snippet": "s", "source_span": {}}]),
    )

    provider = MagicMock()
    provider.model_name = "test-model"

    async def stream_text(prompt):
        for t in ["Conclusion: 建议复查。", "\nEvidence: 两周后复查。"]:
            yield t

    provider.stream_text = stream_text
    provider.complete_text = AsyncMock(
        return_value='{"statements":[{"text":"建议复查","refs":["Doc 1"]}]}'
    )

    monkeypatch.setattr("app.api.endpoints.biz.chat.registry.get_llm", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.biz.chat.check_quota_during_stream", AsyncMock(return_value=True))
    monkeypatch.setattr("app.api.endpoints.biz.chat.update_org_quota", AsyncMock())
    monkeypatch.setattr("app.api.endpoints.biz.chat.count_tokens", lambda text, model="": len(text) // 4)
    dummy_db.objects[(KnowledgeBase, kb_id)] = MagicMock(org_id=current_org)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1", json={
            "kb_id": str(kb_id),
            "conversation_id": str(uuid4()),
            "query": "血糖高怎么办？",
            "document_ids": [str(doc_id)],
            "file_types": ["pdf"],
        })

    assert resp.status_code == 200
    body = resp.text
    assert "event: meta" in body
    assert "event: chunk" in body
    assert "event: done" in body
    assert "statement_citations" in body

    # 验证持久化
    assistant_msg = dummy_db.added[-2]
    usage_log = dummy_db.added[-1]
    assert assistant_msg.metadata_["citations"][0]["page"] == 2
    assert assistant_msg.metadata_["observability"]["raw_query"] == "血糖高怎么办？"
    assert assistant_msg.metadata_["observability"]["llm_model"] == "test-model"
    assert usage_log.model == "test-model"


@pytest.mark.asyncio
async def test_chat_with_empty_query(monkeypatch):
    dummy_db.added.clear()
    dummy_db.commits = 0
    dummy_db.objects = {}
    kb_id = uuid4()

    monkeypatch.setattr(
        "app.api.endpoints.biz.chat.retrieve_chunks",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.api.endpoints.biz.chat.build_rag_prompt",
        lambda q, c: ("prompt", []),
    )

    provider = MagicMock()
    provider.model_name = "t"

    async def stream_text(prompt):
        yield "无相关信息。"

    provider.stream_text = stream_text
    provider.complete_text = AsyncMock(return_value='{"statements":[]}')
    monkeypatch.setattr("app.api.endpoints.biz.chat.registry.get_llm", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.biz.chat.check_quota_during_stream", AsyncMock(return_value=True))
    monkeypatch.setattr("app.api.endpoints.biz.chat.update_org_quota", AsyncMock())
    monkeypatch.setattr("app.api.endpoints.biz.chat.count_tokens", lambda text, model="": 10)
    dummy_db.objects[(KnowledgeBase, kb_id)] = MagicMock(org_id=current_org)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1", json={
            "kb_id": str(kb_id),
            "conversation_id": str(uuid4()),
            "query": "test",
        })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reject_foreign_conversation(monkeypatch):
    dummy_db.added.clear()
    dummy_db.commits = 0
    dummy_db.objects = {}

    conversation_id = uuid4()
    conversation = MagicMock()
    conversation.id = conversation_id
    conversation.org_id = current_org
    conversation.user_id = uuid4()
    conversation.kb_id = uuid4()
    dummy_db.objects[(KnowledgeBase, conversation.kb_id)] = MagicMock(org_id=current_org)
    dummy_db.objects[(Conversation, conversation_id)] = conversation

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1", json={
            "kb_id": str(conversation.kb_id),
            "conversation_id": str(conversation_id),
            "query": "test",
        })

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Conversation does not belong to current user"


@pytest.mark.asyncio
async def test_reject_chat_for_foreign_kb():
    dummy_db.added.clear()
    dummy_db.commits = 0
    dummy_db.objects = {}

    kb_id = uuid4()
    dummy_db.objects[(KnowledgeBase, kb_id)] = MagicMock(org_id=uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1", json={
            "kb_id": str(kb_id),
            "conversation_id": str(uuid4()),
            "query": "test",
        })

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Not enough permissions"
