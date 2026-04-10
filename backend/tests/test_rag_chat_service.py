from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _ExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _ScalarResult(self._items)


class FakeDB:
    def __init__(self, kb):
        self.kb = kb
        self.added = []
        self.commits = 0
        self.executed = []

    async def get(self, model, object_id):
        if model.__name__ == "KnowledgeBase":
            return self.kb
        return None

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _ExecuteResult([])

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


class FakeStreamDB:
    def __init__(self):
        self.added = []
        self.executed = []
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt, params=None):
        self.executed.append((stmt, params))
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


class FakeLLM:
    model_name = "fake-model"

    async def stream_text(self, prompt):
        for chunk in ("结论", "证据"):
            yield chunk


@pytest.mark.asyncio
async def test_handle_standard_chat_orchestrates_stream_and_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.services.rag import chat_service as service_module

    fake_kb = SimpleNamespace(id=11, tenant_id=100)
    fake_db = FakeDB(kb=fake_kb)
    fake_stream_db = FakeStreamDB()
    fake_user = SimpleNamespace(id=7)
    fake_request = SimpleNamespace(
        kb_id=11,
        query="血压情况如何？",
        conversation_id=None,
        document_ids=None,
        file_types=None,
        patient_id=None,
    )

    async def fake_retrieve_chunks(*args, **kwargs):
        return [
            SimpleNamespace(
                id=301, document_id=401, page_number=2, content="血压 140/90"
            )
        ]

    async def fake_extract_statement_citations_structured(*args, **kwargs):
        return [{"text": "结论", "citations": [{"ref": "Doc 1", "chunk_id": "301"}]}]

    async def fake_check_quota_during_stream(*args, **kwargs):
        return True

    async def fake_update_tenant_quota(*args, **kwargs):
        return None

    monkeypatch.setattr(service_module.provider_service, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(service_module, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(
        service_module,
        "build_rag_prompt",
        lambda query, chunks: ("prompt text", [{"ref": "Doc 1", "chunk_id": "301"}]),
    )
    monkeypatch.setattr(
        service_module,
        "extract_statement_citations_structured",
        fake_extract_statement_citations_structured,
    )
    monkeypatch.setattr(service_module, "count_tokens", lambda text, model: len(text))
    monkeypatch.setattr(
        service_module, "check_quota_during_stream", fake_check_quota_during_stream
    )
    monkeypatch.setattr(service_module, "update_tenant_quota", fake_update_tenant_quota)
    monkeypatch.setattr(service_module, "AsyncSessionLocal", lambda: fake_stream_db)
    monkeypatch.setattr(service_module, "_generate_title", lambda query: "血压情况")

    response = await service_module.handle_standard_chat(
        request=fake_request,
        current_user=fake_user,
        tenant_id=100,
        org_id=200,
        db=fake_db,
    )

    events = []
    async for chunk in response.body_iterator:
        events.append(chunk)

    decoded = "".join(events)
    assert "event: meta" in decoded
    assert "event: chunk" in decoded
    assert "event: done" in decoded

    meta_payload = json.loads(
        decoded.split("event: meta\ndata: ", 1)[1].split("\n\n", 1)[0]
    )
    assert meta_payload["citations"] == [{"ref": "Doc 1", "chunk_id": "301"}]

    assert fake_db.commits == 1
    assert any(getattr(item, "role", None) == "user" for item in fake_db.added)
    assert any(
        getattr(item, "role", None) == "assistant" for item in fake_stream_db.added
    )
    assert any(
        getattr(item, "action_type", None) == "chat" for item in fake_stream_db.added
    )


def test_build_filters_normalizes_optional_request_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.services.rag.chat_service import build_filters

    filters = build_filters(document_ids=[1, 2], file_types=["pdf"], patient_id=3)

    assert filters == {
        "document_ids": [1, 2],
        "file_types": ["pdf"],
        "patient_id": 3,
    }
