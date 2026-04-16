from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from io import BytesIO
from urllib.parse import urlparse

import aioboto3
import pytest
from app.base.config import settings
from app.base.database import AsyncSessionLocal, engine
from app.base.snowflake import get_next_id
from app.base.storage import get_storage_service
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import UploadFile
from sqlalchemy import delete

from app.models import Document, KnowledgeBase, Organization, Tenant, User
from app.tasks.worker import WorkerSettings

TEST_REDIS_SETTINGS = RedisSettings(host="localhost", port=6379, database=15)


async def _ensure_bucket_exists(s3) -> None:
    try:
        await s3.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
    except Exception:
        await s3.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)


def _parse_minio_url(minio_url: str) -> tuple[str, str]:
    parsed = urlparse(minio_url)
    path = parsed.path.lstrip("/")
    bucket, _, key = path.partition("/")
    if not bucket or not key:
        raise AssertionError(f"Invalid MinIO URL: {minio_url}")
    return bucket, key


async def _object_exists(s3, minio_url: str) -> bool:
    bucket, key = _parse_minio_url(minio_url)
    try:
        await s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


@pytest.fixture
async def minio_client() -> AsyncIterator:
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.MINIO_URL,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    ) as s3:
        await _ensure_bucket_exists(s3)
        yield s3


@pytest.fixture
async def tracked_minio_urls() -> AsyncIterator[list[str]]:
    urls: list[str] = []
    try:
        yield urls
    finally:
        storage = get_storage_service()
        for minio_url in urls:
            await storage.delete_file(minio_url)


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
async def kb_context() -> AsyncIterator[dict[str, object]]:
    tenant = Tenant(
        id=get_next_id(),
        name="MinIO Integration Tenant",
        slug=f"minio-it-{get_next_id()}",
        status="active",
        plan_type="enterprise",
    )
    user = User(
        id=get_next_id(),
        email=f"minio-{get_next_id()}@example.com",
        password_hash="x",
        name="MinIO Integration User",
    )
    organization = Organization(
        id=get_next_id(),
        tenant_id=tenant.id,
        name="MinIO Integration Org",
        code=f"MINIO-ORG-{get_next_id()}",
        status="active",
    )
    kb = KnowledgeBase(
        id=get_next_id(),
        tenant_id=tenant.id,
        org_id=organization.id,
        created_by=user.id,
        name="MinIO Integration KB",
    )

    async with AsyncSessionLocal() as db:
        db.add(tenant)
        db.add(user)
        db.add(organization)
        await db.commit()

        db.add(kb)
        await db.commit()

        try:
            yield {
                "db": db,
                "tenant": tenant,
                "user": user,
                "organization": organization,
                "kb": kb,
            }
        finally:
            await db.close()

    async with AsyncSessionLocal() as cleanup_db:
        await cleanup_db.execute(delete(Document).where(Document.kb_id == kb.id))
        await cleanup_db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb.id))
        await cleanup_db.execute(
            delete(Organization).where(Organization.id == organization.id)
        )
        await cleanup_db.execute(delete(User).where(User.id == user.id))
        await cleanup_db.execute(delete(Tenant).where(Tenant.id == tenant.id))
        await cleanup_db.commit()


@pytest.mark.asyncio
async def test_storage_service_upload_and_delete_real_minio_object(
    minio_client,
    tracked_minio_urls: list[str],
) -> None:
    storage = get_storage_service()
    filename = f"integration-{uuid.uuid4().hex}.txt"
    org_id = f"integration-minio-{uuid.uuid4().hex[:8]}"
    payload = b"minio integration payload"

    minio_url = await storage.upload_file(
        file_bytes=payload,
        filename=filename,
        org_id=org_id,
    )
    tracked_minio_urls.append(minio_url)

    assert await _object_exists(minio_client, minio_url) is True

    deleted = await storage.delete_file(minio_url)

    assert deleted is True
    assert await _object_exists(minio_client, minio_url) is False


@pytest.mark.asyncio
async def test_upload_document_and_enqueue_stores_real_object(
    minio_client,
    kb_context,
    tracked_minio_urls: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.plugins.parser.base import ParseResult
    from app.services.rag import document_service as service_module

    monkeypatch.setattr(
        service_module.provider_service,
        "get_parser_for_filename",
        lambda _filename: type(
            "Parser",
            (),
            {
                "parse": lambda self, file_bytes, filename: ParseResult(
                    text=file_bytes.decode(), pages=["page-1"]
                )
            },
        )(),
    )
    monkeypatch.setattr(
        service_module,
        "enqueue_process_document_job",
        _async_noop,
    )

    upload = UploadFile(
        filename=f"service-{uuid.uuid4().hex}.txt",
        file=BytesIO(b"service integration payload"),
    )
    upload.headers = {"content-type": "text/plain"}

    result = await service_module.upload_document_and_enqueue(
        kb_id=kb_context["kb"].id,
        file=upload,
        patient_id=None,
        current_user=kb_context["user"],
        tenant_id=kb_context["tenant"].id,
        org_id=kb_context["organization"].id,
        db=kb_context["db"],
    )
    tracked_minio_urls.append(result["minio_url"])

    assert await _object_exists(minio_client, result["minio_url"]) is True


@pytest.mark.asyncio
async def test_delete_file_task_removes_real_minio_object(
    minio_client,
    integration_redis,
    tracked_minio_urls: list[str],
) -> None:
    from app.services.rag import tasks as tasks_module

    storage = get_storage_service()
    minio_url = await storage.upload_file(
        file_bytes=b"cleanup payload",
        filename=f"cleanup-{uuid.uuid4().hex}.txt",
        org_id=f"integration-cleanup-{uuid.uuid4().hex[:8]}",
    )
    tracked_minio_urls.append(minio_url)

    await tasks_module.enqueue_delete_file_job(minio_url=minio_url)

    jobs = await integration_redis.queued_jobs()
    job = jobs[0]
    worker_fn = next(
        fn for fn in WorkerSettings.functions if fn.__name__ == job.function
    )
    await worker_fn({}, *job.args, **job.kwargs)

    assert await _object_exists(minio_client, minio_url) is False


async def _async_noop(**kwargs) -> None:
    return None
