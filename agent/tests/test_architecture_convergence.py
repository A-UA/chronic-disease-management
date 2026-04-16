from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_modules_no_longer_depend_on_legacy_provider_or_chat_service() -> None:
    tracked_files = [
        PROJECT_ROOT / "app" / "services" / "rag" / "chat_service.py",
        PROJECT_ROOT / "app" / "routers" / "system" / "external_api.py",
        PROJECT_ROOT / "app" / "ai" / "rag" / "retrieval.py",
        PROJECT_ROOT / "app" / "ai" / "agent" / "graph.py",
        PROJECT_ROOT / "app" / "ai" / "agent" / "memory.py",
        PROJECT_ROOT / "app" / "ai" / "agent" / "skills" / "rag_skill.py",
        PROJECT_ROOT / "app" / "ai" / "agent" / "skills" / "markdown_loader.py",
        PROJECT_ROOT / "app" / "ai" / "rag" / "evaluation.py",
        PROJECT_ROOT / "app" / "ai" / "rag" / "query_rewrite.py",
        PROJECT_ROOT / "app" / "routers" / "system" / "external_api.py",
    ]

    forbidden_imports = (
        "app.plugins.provider_compat",
        "app.ai.rag.ingestion_legacy",
        "app.ai.rag.llm_legacy",
        "app.ai.rag.reranker_legacy",
        "app.ai.rag.chat_service",
    )

    offenders: list[str] = []
    for file_path in tracked_files:
        contents = file_path.read_text(encoding="utf-8")
        for forbidden in forbidden_imports:
            if forbidden in contents:
                offenders.append(
                    f"{file_path.relative_to(PROJECT_ROOT)} -> {forbidden}"
                )

    assert offenders == []


def test_documents_runtime_no_longer_uses_background_tasks() -> None:
    file_path = PROJECT_ROOT / "app" / "routers" / "rag" / "documents_runtime.py"
    contents = file_path.read_text(encoding="utf-8")

    assert "BackgroundTasks" not in contents
