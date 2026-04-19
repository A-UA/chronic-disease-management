import io
import re
import tempfile
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from pymilvus import connections, Collection
from app.config import settings

_KB_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )


def _get_vector_store() -> Milvus:
    return Milvus(
        embedding_function=_get_embeddings(),
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,
    )


def _parse_file(file_bytes: bytes, filename: str) -> str:
    """根据扩展名解析文件内容为文本"""
    ext = Path(filename).suffix.lower()

    if ext in (".txt", ".md"):
        return file_bytes.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            loader = PyPDFLoader(tmp.name)
            pages = loader.load()
            return "\n\n".join(p.page_content for p in pages)

    if ext == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            loader = Docx2txtLoader(tmp.name)
            docs = loader.load()
            return "\n\n".join(d.page_content for d in docs)

    # 默认按 UTF-8 解析
    return file_bytes.decode("utf-8", errors="ignore")


def process_document_to_milvus(
    file_bytes: bytes,
    filename: str,
    kb_id: str,
    org_id: str | None = None,
) -> int:
    """解析文件并写入 Milvus 向量库"""
    text_content = _parse_file(file_bytes, filename)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    texts = splitter.split_text(text_content)

    metadata_base = {
        "kb_id": kb_id,
        "filename": filename,
        "source": filename,
    }
    if org_id:
        metadata_base["org_id"] = org_id

    docs = [
        Document(page_content=txt, metadata={**metadata_base})
        for txt in texts
    ]

    if not docs:
        return 0

    vector_store = _get_vector_store()
    vector_store.add_documents(docs)
    return len(docs)


def delete_vectors_by_kb(kb_id: str) -> int:
    """根据 kb_id 删除 Milvus 中的所有向量"""
    kb_id_str = str(kb_id)
    if not _KB_ID_PATTERN.match(kb_id_str):
        raise ValueError(f"Invalid kb_id format: {kb_id_str}")

    collection_name = f"{settings.MILVUS_COLLECTION_PREFIX}kb"
    alias = "cdm_cleanup"
    connections.connect(alias=alias, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    try:
        col = Collection(collection_name, using=alias)
        expr = f'kb_id == "{kb_id_str}"'
        # 查询命中 ID 计数（Milvus 的 delete 不返回计数）
        col.load()
        results = col.query(expr=expr, output_fields=["pk"])
        count = len(results)
        if count > 0:
            col.delete(expr=expr)
        return count
    finally:
        connections.disconnect(alias)


def delete_vectors_by_doc(kb_id: str, filename: str) -> int:
    """根据 kb_id + filename 删除 Milvus 中指定文档的向量"""
    kb_id_str = str(kb_id)
    if not _KB_ID_PATTERN.match(kb_id_str):
        raise ValueError(f"Invalid kb_id format: {kb_id_str}")

    collection_name = f"{settings.MILVUS_COLLECTION_PREFIX}kb"
    alias = "cdm_cleanup"
    connections.connect(alias=alias, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    try:
        col = Collection(collection_name, using=alias)
        expr = f'kb_id == "{kb_id_str}" && filename == "{filename}"'
        col.load()
        results = col.query(expr=expr, output_fields=["pk"])
        count = len(results)
        if count > 0:
            col.delete(expr=expr)
        return count
    finally:
        connections.disconnect(alias)
