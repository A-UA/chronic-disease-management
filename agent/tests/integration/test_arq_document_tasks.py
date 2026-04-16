from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.base.database import AsyncSessionLocal, engine
from app.base.snowflake import get_next_id
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import delete, select

from app.models import Document, KnowledgeBase, Organization, Tenant, User
from app.tasks.worker import WorkerSettings

TEST_REDIS_SETTINGS = RedisSettings(host="localhost", port=6379, database=15)


@pytest.fixture
async def integration_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator:
    monkeypatch.setattr(WorkerSettings, "redis_settings", TEST_REDIS_SETTINGS)
    redis = await create_pool(TEST_REDIS_SETTINGS)
    await redis.flushdb()
    try:
        yield redis
    finally:
        await redis.flushdb()
        await redis.aclose()
        await engine.dispose()


@pytest.fixture
async def document_record() -> AsyncIterator[Document]:
    tenant = Tenant(
        id=get_next_id(),
        name="Integration Tenant",
        slug=f"it-{get_next_id()}",
        status="active",
        plan_type="enterprise",
    )
    user = User(
        id=get_next_id(),
        email=f"integration-{get_next_id()}@example.com",
        password_hash="x",
        name="Integration User",
    )
    organization = Organization(
        id=get_next_id(),
        tenant_id=tenant.id,
        name="Integration Org",
        code=f"ORG-{get_next_id()}",
        status="active",
    )
    kb = KnowledgeBase(
        id=get_next_id(),
        tenant_id=tenant.id,
        org_id=organization.id,
        created_by=user.id,
        name="Integration KB",
    )
    document = Document(
        id=get_next_id(),
        tenant_id=tenant.id,
        kb_id=kb.id,
        org_id=organization.id,
        uploader_id=user.id,
        file_name="integration.pdf",
        file_type="application/pdf",
        file_size=128,
        minio_url=f"minio://integration/{get_next_id()}",
        status="pending",
    )

    async with AsyncSessionLocal() as db:
        db.add(tenant)
        db.add(user)
        db.add(organization)
        await db.commit()

        db.add(kb)
        await db.commit()

        db.add(document)
        await db.commit()

    try:
        yield document
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Document).where(Document.id == document.id))
            await db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb.id))
            await db.execute(
                delete(Organization).where(Organization.id == organization.id)
            )
            await db.execute(delete(User).where(User.id == user.id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant.id))
            await db.commit()


async def _reload_document(document_id: int) -> Document | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()


def _get_worker_function(function_name: str):
    for fn in WorkerSettings.functions:
        if fn.__name__ == function_name:
            return fn
    raise AssertionError(f"Worker function not registered: {function_name}")


@pytest.mark.asyncio
async def test_enqueue_and_consume_process_document_task_success(
    integration_redis,
    document_record: Document,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ai.rag import ingestion as ingestion_module
    from app.services.rag.provider_service import provider_service

    from app.services.rag import tasks as tasks_module

    async def fake_ingest_document_with_dependencies(**kwargs):
        kwargs["document"].status = "completed"
        kwargs["document"].failed_reason = None
        return 42

    async def fake_update_org_quota(db, org_id, total_tokens):
        return None

    monkeypatch.setattr(
        ingestion_module,
        "ingest_document_with_dependencies",
        fake_ingest_document_with_dependencies,
    )
    monkeypatch.setattr(provider_service, "get_chunker", lambda: object())
    monkeypatch.setattr(provider_service, "get_embedding", lambda: object())
    monkeypatch.setattr(provider_service, "get_llm", lambda: object())
    monkeypatch.setattr(
        "app.services.system.quota.update_org_quota",
        fake_update_org_quota,
    )

    await tasks_module.enqueue_process_document_job(
        document_id=document_record.id,
        file_content="hello",
        org_id=document_record.org_id,
        pages=["p1"],
    )

    jobs = await integration_redis.queued_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.function == "process_document_task"

    worker_fn = _get_worker_function(job.function)
    await worker_fn({}, *job.args, **job.kwargs)

    reloaded = await _reload_document(document_record.id)
    assert reloaded is not None
    assert reloaded.status == "completed"
    assert reloaded.failed_reason is None


@pytest.mark.asyncio
async def test_enqueue_and_consume_process_document_task_failure_writes_back_status(
    integration_redis,
    document_record: Document,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ai.rag import ingestion as ingestion_module
    from app.services.rag.provider_service import provider_service

    from app.services.rag import tasks as tasks_module

    async def fake_ingest_document_with_dependencies(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        ingestion_module,
        "ingest_document_with_dependencies",
        fake_ingest_document_with_dependencies,
    )
    monkeypatch.setattr(provider_service, "get_chunker", lambda: object())
    monkeypatch.setattr(provider_service, "get_embedding", lambda: object())
    monkeypatch.setattr(provider_service, "get_llm", lambda: object())

    await tasks_module.enqueue_process_document_job(
        document_id=document_record.id,
        file_content="hello",
        org_id=document_record.org_id,
        pages=["p1"],
    )

    jobs = await integration_redis.queued_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    worker_fn = _get_worker_function(job.function)

    with pytest.raises(RuntimeError, match="boom"):
        await worker_fn({}, *job.args, **job.kwargs)

    reloaded = await _reload_document(document_record.id)
    assert reloaded is not None
    assert reloaded.status == "failed"
    assert reloaded.failed_reason == "boom"


@pytest.mark.asyncio
async def test_enqueue_and_consume_delete_file_task(
    integration_redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.rag import tasks as tasks_module

    deleted_urls: list[str] = []

    async def fake_delete_file(self, minio_url: str) -> bool:
        deleted_urls.append(minio_url)
        return True

    monkeypatch.setattr(
        "app.base.storage.get_storage_service",
        lambda: type("Storage", (), {"delete_file": fake_delete_file})(),
    )

    await tasks_module.enqueue_delete_file_job(minio_url="minio://bucket/object.pdf")

    jobs = await integration_redis.queued_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.function == "delete_file_task"

    worker_fn = _get_worker_function(job.function)
    await worker_fn({}, *job.args, **job.kwargs)

    assert deleted_urls == ["minio://bucket/object.pdf"]
