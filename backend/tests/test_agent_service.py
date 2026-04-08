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

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalars(self):
        return _ScalarResult(self._items)


class FakeDB:
    def __init__(self, org_user=None, roles=None):
        self.org_user = org_user
        self.roles = roles or []
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        text = str(stmt)
        if "organization_users" in text:
            return _ExecuteResult([self.org_user] if self.org_user else [])
        if "organization_user_roles" in text:
            return _ExecuteResult(self.roles)
        return _ExecuteResult([])

    async def get(self, model, object_id):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


class FakeSaveDB:
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

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_handle_agent_chat_builds_security_context_and_persists_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.services.agent import service as service_module

    fake_db = FakeDB(
        org_user=SimpleNamespace(id=55),
        roles=[SimpleNamespace(role_id=701)],
    )
    fake_save_db = FakeSaveDB()
    fake_user = SimpleNamespace(id=7)
    fake_request = SimpleNamespace(
        kb_id=11,
        query="分析一下最近血压趋势",
        conversation_id=None,
    )

    async def fake_build_agent_permissions(db, role_ids):
        assert role_ids == [701]
        return {"patient:read", "chat:use"}

    captured = {}

    async def fake_run_agent(*, ctx, query, kb_id, conversation_id):
        captured["ctx"] = ctx
        captured["query"] = query
        captured["kb_id"] = kb_id
        captured["conversation_id"] = conversation_id
        return {
            "answer": "这是 agent 结论",
            "citations": [{"ref": "Doc 1"}],
            "skill_results": [{"skill": "rag_search"}],
        }

    monkeypatch.setattr(service_module, "build_agent_permissions", fake_build_agent_permissions)
    monkeypatch.setattr(service_module, "run_agent", fake_run_agent)
    monkeypatch.setattr(service_module, "AsyncSessionLocal", lambda: fake_save_db)
    monkeypatch.setattr(service_module, "_generate_title", lambda query: "血压趋势")

    response = await service_module.handle_agent_chat(
        request=fake_request,
        db=fake_db,
        tenant_id=100,
        org_id=200,
        current_user=fake_user,
    )

    events = []
    async for chunk in response.body_iterator:
        events.append(chunk)

    decoded = "".join(events)
    assert "event: meta" in decoded
    assert "event: chunk" in decoded
    assert "event: done" in decoded

    meta_payload = json.loads(decoded.split("event: meta\ndata: ", 1)[1].split("\n\n", 1)[0])
    assert meta_payload["citations"] == [{"ref": "Doc 1"}]
    assert captured["ctx"].permissions == frozenset({"patient:read", "chat:use"})
    assert any(getattr(item, "role", None) == "user" for item in fake_db.added)
    assert any(getattr(item, "role", None) == "assistant" for item in fake_save_db.added)
