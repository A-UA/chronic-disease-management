"""Chat route integration tests — /api/v1/chat

涵盖三个场景：
1. Standard chat (use_agent=false)：SSE meta→chunk→done 流 + 数据库持久化
2. Agent chat (use_agent=true)：SSE meta→chunk→done 流 + agent_mode 元数据
3. Failure visibility：下游异常在 SSE 流中可见（error 事件）
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
from app.base.database import AsyncSessionLocal, engine
from app.base.security import create_access_token
from app.base.snowflake import get_next_id
from app.routers.deps import (
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_db,
    verify_quota,
)
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import (
    Conversation,
    KnowledgeBase,
    Message,
    Organization,
    Tenant,
    User,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse(raw: str) -> list[dict]:
    """将 text/event-stream 原始文本解析为 [{event, data}, ...]"""
    events: list[dict] = []
    current_event = ""
    current_data = ""
    for line in raw.split("\n"):
        if line.startswith("event: "):
            current_event = line[len("event: ") :]
        elif line.startswith("data: "):
            current_data = line[len("data: ") :]
        elif line == "":
            if current_event:
                try:
                    parsed = json.loads(current_data)
                except (json.JSONDecodeError, TypeError):
                    parsed = current_data
                events.append({"event": current_event, "data": parsed})
            current_event = ""
            current_data = ""
    return events


# ---------------------------------------------------------------------------
# Seed data fixture — 创建 Tenant → Org → User → KB，测试结束后清理
# ---------------------------------------------------------------------------


class _SeedData:
    def __init__(
        self,
        tenant: Tenant,
        org: Organization,
        user: User,
        kb: KnowledgeBase,
        token: str,
    ):
        self.tenant = tenant
        self.org = org
        self.user = user
        self.kb = kb
        self.token = token


@pytest.fixture
async def seed() -> AsyncIterator[_SeedData]:
    tenant = Tenant(
        id=get_next_id(),
        name="Chat Test Tenant",
        slug=f"ctt-{get_next_id()}",
        status="active",
        plan_type="enterprise",
        quota_tokens_limit=999_999_999,
        quota_tokens_used=0,
    )
    user = User(
        id=get_next_id(),
        email=f"chattest-{get_next_id()}@example.com",
        password_hash="x",
        name="Chat Test User",
    )
    org = Organization(
        id=get_next_id(),
        tenant_id=tenant.id,
        name="Chat Test Org",
        code=f"CTO-{get_next_id()}",
        status="active",
    )
    kb = KnowledgeBase(
        id=get_next_id(),
        tenant_id=tenant.id,
        org_id=org.id,
        created_by=user.id,
        name="Chat Test KB",
    )

    async with AsyncSessionLocal() as db:
        # 设置 RLS 上下文（跳过 RLS 限制写入种子数据）
        await db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(tenant.id)},
        )
        await db.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user.id)},
        )
        db.add(tenant)
        db.add(user)
        db.add(org)
        await db.commit()
        db.add(kb)
        await db.commit()

    token = create_access_token(
        subject=user.id,
        tenant_id=tenant.id,
        org_id=org.id,
        roles=["admin"],
    )
    try:
        yield _SeedData(tenant=tenant, org=org, user=user, kb=kb, token=token)
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant.id)},
            )
            # 按依赖反向删除
            await db.execute(
                delete(Message).where(
                    Message.conversation_id.in_(
                        select(Conversation.id).where(
                            Conversation.tenant_id == tenant.id
                        )
                    )
                )
            )
            await db.execute(
                delete(Conversation).where(Conversation.tenant_id == tenant.id)
            )
            await db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb.id))
            await db.execute(delete(Organization).where(Organization.id == org.id))
            await db.execute(delete(User).where(User.id == user.id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant.id))
            await db.commit()
        await engine.dispose()


# ---------------------------------------------------------------------------
# Dependency overrides fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def _override_deps(seed: _SeedData):
    """覆写 FastAPI 依赖，消除 JWT 解析和配额校验"""

    async def _fake_user() -> User:
        return seed.user

    async def _fake_tenant_id() -> int:
        return seed.tenant.id

    async def _fake_org_id() -> int:
        return seed.org.id

    async def _fake_quota():
        return seed.tenant

    async def _fake_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(seed.tenant.id)},
            )
            await session.execute(
                text("SELECT set_config('app.current_user_id', :uid, true)"),
                {"uid": str(seed.user.id)},
            )
            yield session

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_current_tenant_id] = _fake_tenant_id
    app.dependency_overrides[get_current_org_id] = _fake_org_id
    app.dependency_overrides[verify_quota] = _fake_quota
    app.dependency_overrides[get_db] = _fake_db

    yield

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Task 1: Standard chat route integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_standard_chat_sse_and_persistence(
    seed: _SeedData,
    _override_deps,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """标准 chat 流程：meta → chunk → done 事件 + Conversation/Message 持久化"""

    # ── Stub AI 层 ──
    # 1) retrieve_chunks → 返回空列表（无向量检索）
    monkeypatch.setattr(
        "app.services.rag.chat_service.retrieve_chunks",
        AsyncMock(return_value=[]),
    )
    # 2) build_rag_prompt → 返回 (prompt_text, [])
    monkeypatch.setattr(
        "app.services.rag.chat_service.build_rag_prompt",
        lambda query, chunks: ("fake prompt", []),
    )
    # 3) extract_statement_citations_structured → 无引用映射
    monkeypatch.setattr(
        "app.services.rag.chat_service.extract_statement_citations_structured",
        AsyncMock(return_value=[]),
    )
    # 4) count_tokens → 固定值
    monkeypatch.setattr(
        "app.services.rag.chat_service.count_tokens",
        lambda text, model: 10,
    )
    # 5) quota 相关
    monkeypatch.setattr(
        "app.services.rag.chat_service.check_quota_during_stream",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.services.rag.chat_service.update_tenant_quota",
        AsyncMock(),
    )

    # 6) LLM provider → 伪造 stream_text
    class FakeLLM:
        model_name = "test-model"

        async def stream_text(self, prompt):
            for word in ["Hello", " ", "World"]:
                yield word

    monkeypatch.setattr(
        "app.services.rag.chat_service.provider_service",
        type("FakePS", (), {"get_llm": staticmethod(lambda: FakeLLM())})(),
    )

    # ── 发起请求 ──
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.post(
            "/api/v1/chat",
            json={
                "kb_id": seed.kb.id,
                "query": "测试标准对话",
                "use_agent": False,
            },
            headers={"Authorization": f"Bearer {seed.token}"},
        )

    # ── 断言 HTTP 层 ──
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    event_types = [e["event"] for e in events]
    assert "meta" in event_types
    assert "chunk" in event_types
    assert "done" in event_types

    # meta 包含 conversation_id
    meta = next(e for e in events if e["event"] == "meta")
    conversation_id = int(meta["data"]["conversation_id"])
    assert conversation_id > 0

    # chunk 内容拼接
    chunks_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")
    assert chunks_text == "Hello World"

    # ── 断言数据库持久化 ──
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(seed.tenant.id)},
        )
        conv = await db.get(Conversation, conversation_id)
        assert conv is not None
        assert conv.user_id == seed.user.id
        assert conv.kb_id == seed.kb.id

        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        msgs = msg_result.scalars().all()
        roles = {m.role for m in msgs}
        assert "user" in roles
        assert "assistant" in roles


# ---------------------------------------------------------------------------
# Task 2: Agent chat route integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_chat_sse_and_metadata(
    seed: _SeedData,
    _override_deps,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent chat 流程：SSE meta → chunk → done + assistant message 含 agent_mode"""

    # ── Stub run_agent ──
    async def fake_run_agent(*, ctx, query, kb_id, conversation_id):
        return {
            "answer": "Agent answer",
            "citations": [{"ref": "1", "title": "test"}],
            "skill_results": [{"skill": "rag", "status": "ok"}],
        }

    monkeypatch.setattr(
        "app.services.agent.service.run_agent",
        fake_run_agent,
    )

    # Stub OrganizationUser / OrganizationUserRole 查询
    # handle_agent_chat 内部会查 org_user 和 role_ids
    # 让查询返回空即可（effective_perms = frozenset()）
    monkeypatch.setattr(
        "app.services.agent.service.build_agent_permissions",
        AsyncMock(return_value=set()),
    )

    # ── 发起请求 ──
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.post(
            "/api/v1/chat",
            json={
                "kb_id": seed.kb.id,
                "query": "测试 Agent 对话",
                "use_agent": True,
            },
            headers={"Authorization": f"Bearer {seed.token}"},
        )

    # ── 断言 HTTP 层 ──
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    event_types = [e["event"] for e in events]
    assert "meta" in event_types
    assert "chunk" in event_types
    assert "done" in event_types

    # meta 包含 conversation_id 和 citations
    meta = next(e for e in events if e["event"] == "meta")
    conversation_id = int(meta["data"]["conversation_id"])
    assert conversation_id > 0
    assert meta["data"]["citations"] == [{"ref": "1", "title": "test"}]

    # chunk 内容
    chunk_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")
    assert chunk_text == "Agent answer"

    # done 事件含 skill_results
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["skill_results"] == [{"skill": "rag", "status": "ok"}]

    # ── 断言数据库持久化 ──
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(seed.tenant.id)},
        )
        msg_result = await db.execute(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
            )
        )
        assistant_msg = msg_result.scalar_one_or_none()
        assert assistant_msg is not None
        assert assistant_msg.metadata_ is not None
        assert assistant_msg.metadata_.get("agent_mode") is True


# ---------------------------------------------------------------------------
# Task 3: Failure visibility — 下游异常在 SSE 流中可见
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_standard_chat_failure_surfaces_error_event(
    seed: _SeedData,
    _override_deps,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """当 LLM streaming 抛出异常时，SSE 流应包含 error 事件"""

    # ── Stub AI 层（与 Task 1 类似，但 LLM 抛异常） ──
    monkeypatch.setattr(
        "app.services.rag.chat_service.retrieve_chunks",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.rag.chat_service.build_rag_prompt",
        lambda query, chunks: ("fake prompt", []),
    )
    monkeypatch.setattr(
        "app.services.rag.chat_service.count_tokens",
        lambda text, model: 10,
    )
    monkeypatch.setattr(
        "app.services.rag.chat_service.check_quota_during_stream",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.services.rag.chat_service.update_tenant_quota",
        AsyncMock(),
    )

    # LLM provider 抛异常
    class ExplodingLLM:
        model_name = "test-model"

        async def stream_text(self, prompt):
            raise RuntimeError("LLM connection failed")
            # make it an async generator
            yield  # noqa: unreachable — 保证是 async generator

    monkeypatch.setattr(
        "app.services.rag.chat_service.provider_service",
        type("FakePS", (), {"get_llm": staticmethod(lambda: ExplodingLLM())})(),
    )

    # ── 发起请求 ──
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.post(
            "/api/v1/chat",
            json={
                "kb_id": seed.kb.id,
                "query": "测试异常流",
                "use_agent": False,
            },
            headers={"Authorization": f"Bearer {seed.token}"},
        )

    # 即使下游失败，HTTP 层依然是 200（因为流已经开始）
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    event_types = [e["event"] for e in events]

    # meta 正常发出
    assert "meta" in event_types
    # 应该有 error 事件
    assert "error" in event_types

    error_event = next(e for e in events if e["event"] == "error")
    assert "detail" in error_event["data"]
