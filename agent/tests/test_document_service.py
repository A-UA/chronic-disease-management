from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, chunks: list[bytes]):
        self.filename = filename
        self.content_type = content_type
        self._chunks = list(chunks)

    async def read(self, _size: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _ScalarOneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDB:
    def __init__(self, kb, patient_exists=True):
        self.kb = kb
        self.patient_exists = patient_exists
        self.added = []
        self.commits = 0

    async def get(self, model, object_id):
        if model.__name__ == "KnowledgeBase":
            return self.kb
        return None

    async def execute(self, stmt):
        return _ScalarOneResult(1 if self.patient_exists else None)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, document):
        document.id = 9001


class FakeDeleteDB:
    def __init__(self):
        self.executed = []
        self.commits = 0
        self.deleted = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        return None

    async def delete(self, obj):
        self.deleted.append(obj)
        
    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_upload_document_and_enqueue_uses_parser_storage_and_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.services.rag import document_service as service_module

    fake_db = FakeDB(kb=SimpleNamespace(id=11, tenant_id=100))
    fake_user = SimpleNamespace(id=7)
    fake_file = FakeUploadFile("report.pdf", "application/pdf", [b"abc", b"def"])
    fake_parser = SimpleNamespace(
        parse=lambda file_bytes, filename: SimpleNamespace(
            text="parsed text", pages=["page-1"]
        )
    )

    enqueue_calls = []

    async def fake_enqueue_process_document_job(**kwargs):
        enqueue_calls.append(kwargs)

    monkeypatch.setattr(
        service_module.provider_service,
        "get_parser_for_filename",
        lambda filename: fake_parser,
    )
    monkeypatch.setattr(
        service_module,
        "get_storage_service",
        lambda: SimpleNamespace(
            upload_file=_async_return("minio://report.pdf"),
        ),
    )
    monkeypatch.setattr(
        service_module,
        "enqueue_process_document_job",
        fake_enqueue_process_document_job,
    )

    result = await service_module.upload_document_and_enqueue(
        kb_id=11,
        file=fake_file,
        patient_id=None,
        current_user=fake_user,
        tenant_id=100,
        org_id=200,
        db=fake_db,
    )

    assert result == {
        "id": 9001,
        "minio_url": "minio://report.pdf",
        "status": "pending",
    }
    assert fake_db.commits == 1
    assert enqueue_calls == [
        {
            "document_id": 9001,
            "file_content": "parsed text",
            "org_id": 200,
            "pages": ["page-1"],
        }
    ]


@pytest.mark.asyncio
async def test_upload_document_and_enqueue_marks_document_failed_when_queue_submission_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.services.rag import document_service as service_module

    fake_db = FakeDB(kb=SimpleNamespace(id=11, tenant_id=100))
    fake_user = SimpleNamespace(id=7)
    fake_file = FakeUploadFile("report.pdf", "application/pdf", [b"abc"])
    fake_parser = SimpleNamespace(
        parse=lambda file_bytes, filename: SimpleNamespace(
            text="parsed text", pages=["page-1"]
        )
    )

    async def fake_enqueue_process_document_job(**kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        service_module.provider_service,
        "get_parser_for_filename",
        lambda filename: fake_parser,
    )
    monkeypatch.setattr(
        service_module,
        "get_storage_service",
        lambda: SimpleNamespace(
            upload_file=_async_return("minio://report.pdf"),
        ),
    )
    monkeypatch.setattr(
        service_module,
        "enqueue_process_document_job",
        fake_enqueue_process_document_job,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service_module.upload_document_and_enqueue(
            kb_id=11,
            file=fake_file,
            patient_id=None,
            current_user=fake_user,
            tenant_id=100,
            org_id=200,
            db=fake_db,
        )

    document = fake_db.added[0]
    assert exc_info.value.status_code == 500
    assert document.status == "failed"
    assert document.failed_reason == "enqueue_failed: RuntimeError"
    assert fake_db.commits == 2


def _async_return(value):
    async def _inner(**kwargs):
        return value

    return _inner


@pytest.mark.asyncio
async def test_delete_document_and_enqueue_cleanup_deletes_after_queue_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.services.rag import document_service as service_module

    fake_db = FakeDeleteDB()
    document = SimpleNamespace(id=77, minio_url="minio://report.pdf")
    calls = []

    async def fake_enqueue_delete_file_job(*, minio_url: str) -> None:
        calls.append(minio_url)

    monkeypatch.setattr(
        service_module,
        "enqueue_delete_file_job",
        fake_enqueue_delete_file_job,
    )

    await service_module.delete_document_and_enqueue_cleanup(
        document=document,
        db=fake_db,
    )

    assert calls == ["minio://report.pdf"]
    assert fake_db.commits == 1
    assert len(fake_db.deleted) == 1


@pytest.mark.asyncio
async def test_delete_document_and_enqueue_cleanup_does_not_commit_when_queue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.services.rag import document_service as service_module

    fake_db = FakeDeleteDB()
    document = SimpleNamespace(id=77, minio_url="minio://report.pdf")

    async def fake_enqueue_delete_file_job(*, minio_url: str) -> None:
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        service_module,
        "enqueue_delete_file_job",
        fake_enqueue_delete_file_job,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service_module.delete_document_and_enqueue_cleanup(
            document=document,
            db=fake_db,
        )

    assert exc_info.value.status_code == 500
    assert fake_db.commits == 0
    assert fake_db.executed == []
