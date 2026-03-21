from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_org, get_current_user, get_db
from app.api.endpoints.documents import router


app = FastAPI()
app.include_router(router, prefix="/api/v1")


class DummyUser:
    def __init__(self):
        self.id = uuid4()


class DummyDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        self.refreshed = True


dummy_db = DummyDB()


async def override_get_db():
    yield dummy_db


async def override_get_current_user():
    return DummyUser()


async def override_get_current_org():
    return uuid4()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_current_org] = override_get_current_org


def build_docx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
            </Types>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>随访记录</w:t></w:r></w:p>
                </w:body>
            </w:document>""",
        )
    return buffer.getvalue()


def build_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 31 >> stream\n"
        b"BT (PDF intake note) Tj ET\n"
        b"endstream endobj\n"
        b"trailer << /Root 1 0 R >>\n"
        b"%%EOF"
    )


@pytest.mark.asyncio
async def test_upload_document_rejects_unsupported_file_before_storage(monkeypatch):
    calls = {"upload": 0}

    def fake_upload_file(*args, **kwargs):
        calls["upload"] += 1
        return "http://minio/documents/test"

    monkeypatch.setattr("app.api.endpoints.documents.storage_service.upload_file", fake_upload_file)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/kb/{uuid4()}/documents",
            files={"file": ("image.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        )

    assert response.status_code == 400
    assert "Unsupported document type" in response.json()["detail"]
    assert calls["upload"] == 0
    assert dummy_db.added == []


@pytest.mark.asyncio
async def test_upload_document_accepts_docx_and_stores_after_parse(monkeypatch):
    dummy_db.added.clear()
    dummy_db.committed = False
    dummy_db.refreshed = False

    calls = {"upload": 0, "background": 0}

    def fake_upload_file(*args, **kwargs):
        calls["upload"] += 1
        return "http://minio/documents/test"

    async def fake_process_document(*args, **kwargs):
        calls["background"] += 1

    monkeypatch.setattr("app.api.endpoints.documents.storage_service.upload_file", fake_upload_file)
    monkeypatch.setattr("app.api.endpoints.documents.process_document", fake_process_document)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/kb/{uuid4()}/documents",
            files={
                "file": (
                    "note.docx",
                    build_docx_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    assert calls["upload"] == 1
    assert dummy_db.committed is True
    assert dummy_db.refreshed is True
    assert len(dummy_db.added) == 1


@pytest.mark.asyncio
async def test_upload_document_accepts_pdf_and_stores_after_parse(monkeypatch):
    dummy_db.added.clear()
    dummy_db.committed = False
    dummy_db.refreshed = False

    calls = {"upload": 0}

    def fake_upload_file(*args, **kwargs):
        calls["upload"] += 1
        return "http://minio/documents/test"

    async def fake_process_document(*args, **kwargs):
        return None

    monkeypatch.setattr("app.api.endpoints.documents.storage_service.upload_file", fake_upload_file)
    monkeypatch.setattr("app.api.endpoints.documents.process_document", fake_process_document)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/kb/{uuid4()}/documents",
            files={"file": ("note.pdf", build_pdf_bytes(), "application/pdf")},
        )

    assert response.status_code == 200
    assert calls["upload"] == 1
    assert dummy_db.committed is True
    assert len(dummy_db.added) == 1
