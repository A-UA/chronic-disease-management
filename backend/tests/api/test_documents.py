"""Document upload API 测试"""
from io import BytesIO
from uuid import uuid4
from unittest.mock import MagicMock
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

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()


dummy_db = DummyDB()

async def override_db():
    yield dummy_db

app.dependency_overrides[get_db] = override_db
app.dependency_overrides[get_current_user] = lambda: DummyUser()
app.dependency_overrides[get_current_org] = lambda: uuid4()


def _docx_bytes():
    buf = BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
        z.writestr("word/document.xml", '''<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body><w:p><w:r><w:t>测试</w:t></w:r></w:p></w:body>
</w:document>''')
    return buf.getvalue()


@pytest.mark.asyncio
async def test_reject_unsupported(monkeypatch):
    storage = MagicMock()
    storage.upload_file = MagicMock()  # 不应被调用
    monkeypatch.setattr("app.api.endpoints.documents.get_storage_service", lambda: storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/kb/{uuid4()}/documents",
            files={"file": ("img.png", b"\x89PNG", "image/png")},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_docx(monkeypatch):
    dummy_db.added.clear()
    dummy_db.committed = False

    async def fake_upload(*a, **kw):
        return "http://minio/test"

    storage = MagicMock()
    storage.upload_file = fake_upload
    monkeypatch.setattr("app.api.endpoints.documents.get_storage_service", lambda: storage)
    monkeypatch.setattr("app.api.endpoints.documents.process_document", lambda *a, **kw: None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/v1/kb/{uuid4()}/documents",
            files={"file": ("note.docx", _docx_bytes(),
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert resp.status_code == 200
    assert dummy_db.committed
