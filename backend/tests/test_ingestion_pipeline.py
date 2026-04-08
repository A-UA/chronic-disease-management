from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


INGESTION_FILE = Path(__file__).resolve().parents[1] / "app" / "ai" / "rag" / "ingestion.py"


def test_ingestion_module_no_longer_owns_session_or_quota_side_effects() -> None:
    source = INGESTION_FILE.read_text(encoding="utf-8")

    assert "from app.base.database import AsyncSessionLocal" not in source
    assert "from app.services.system.quota import update_org_quota" not in source
    assert "async with AsyncSessionLocal()" not in source


@pytest.mark.asyncio
async def test_ingest_document_with_dependencies_uses_injected_session_and_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("API_KEY_SALT", "test-salt")

    from app.ai.rag import ingestion as ingestion_module

    fake_db = SimpleNamespace(added=[])
    fake_db.add = fake_db.added.append

    document = SimpleNamespace(
        id=501,
        tenant_id=100,
        kb_id=11,
        org_id=200,
        uploader_id=7,
        patient_id=None,
        file_name="report.pdf",
        status="pending",
        failed_reason="old",
    )

    chunker = SimpleNamespace(
        chunk=lambda text, pages=None: [
            SimpleNamespace(
                content="血压 140/90",
                page_number=1,
                section_title="检验结果",
                char_start=0,
                char_end=9,
            )
        ]
    )
    embedding_provider = SimpleNamespace(
        embed_documents=_async_return([[0.1, 0.2]]),
        get_dimension=lambda: 2,
        model_name="embedding-test",
    )
    llm_provider = SimpleNamespace(complete_text=_async_return("context"))

    total_tokens = await ingestion_module.ingest_document_with_dependencies(
        db=fake_db,
        document=document,
        file_content="血压 140/90",
        pages=["血压 140/90"],
        chunker=chunker,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
        contextual_ingestion=False,
    )

    assert total_tokens > 0
    assert document.status == "completed"
    assert document.failed_reason is None
    assert any(getattr(item, "chunk_index", None) == 0 for item in fake_db.added)
    assert any(getattr(item, "action_type", None) == "embedding" for item in fake_db.added)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner
