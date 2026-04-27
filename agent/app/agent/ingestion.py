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

# 正则表达式：用于校验 kb_id 格式，防止注入攻击
_KB_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _get_embeddings() -> OpenAIEmbeddings:
    """获取 OpenAI Embeddings 实例"""
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )


def _get_vector_store() -> Milvus:
    """获取 Milvus 向量存储实例"""
    return Milvus(
        embedding_function=_get_embeddings(),
        connection_args={"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT},
        collection_name=f"{settings.MILVUS_COLLECTION_PREFIX}kb",
        auto_id=True,  # 自动生成主键 ID
    )


def _parse_file(file_bytes: bytes, filename: str) -> str:
    """根据扩展名解析文件内容为文本串"""
    ext = Path(filename).suffix.lower()

    # 处理纯文本和 Markdown
    if ext in (".txt", ".md"):
        return file_bytes.decode("utf-8", errors="ignore")

    # 处理 PDF：使用临时文件和 PyPDFLoader
    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            loader = PyPDFLoader(tmp.name)
            pages = loader.load()
            return "\n\n".join(p.page_content for p in pages)

    # 处理 DOCX：使用临时文件和 Docx2txtLoader
    if ext == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            loader = Docx2txtLoader(tmp.name)
            docs = loader.load()
            return "\n\n".join(d.page_content for d in docs)

    # 默认兜底处理
    return file_bytes.decode("utf-8", errors="ignore")


def process_document_to_milvus(
    file_bytes: bytes,
    filename: str,
    kb_id: str,
    org_id: str | None = None,
) -> int:
    """核心逻辑：解析、切片并持久化到 Milvus"""
    # 1. 提取文本内容
    text_content = _parse_file(file_bytes, filename)

    # 2. 初始化切片器：每块 1000 字符，重叠 150 字符以保留语义连续性
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    texts = splitter.split_text(text_content)

    # 3. 构造元数据
    metadata_base = {
        "kb_id": kb_id,
        "filename": filename,
        "source": filename,
    }
    if org_id:
        metadata_base["org_id"] = org_id

    # 4. 封装为 LangChain Document 对象
    docs = [
        Document(page_content=txt, metadata={**metadata_base})
        for txt in texts
    ]

    if not docs:
        return 0

    # 5. 批量写入向量库
    vector_store = _get_vector_store()
    vector_store.add_documents(docs)
    return len(docs)


def delete_vectors_by_kb(kb_id: str) -> int:
    """根据 kb_id 删除 Milvus 中的所有向量块"""
    kb_id_str = str(kb_id)
    # 校验合法性
    if not _KB_ID_PATTERN.match(kb_id_str):
        raise ValueError(f"Invalid kb_id format: {kb_id_str}")

    collection_name = f"{settings.MILVUS_COLLECTION_PREFIX}kb"
    alias = "cdm_cleanup"
    # 创建独立连接进行清理操作
    connections.connect(alias=alias, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    try:
        col = Collection(collection_name, using=alias)
        expr = f'kb_id == "{kb_id_str}"'
        # 在删除前查询命中数量（Milvus delete 接口本身不直接返回删除数）
        col.load()
        results = col.query(expr=expr, output_fields=["pk"])
        count = len(results)
        if count > 0:
            # 执行物理删除
            col.delete(expr=expr)
        return count
    finally:
        connections.disconnect(alias)


def delete_vectors_by_doc(kb_id: str, filename: str) -> int:
    """根据 kb_id + filename 删除特定文档的向量块"""
    kb_id_str = str(kb_id)
    # 校验合法性
    if not _KB_ID_PATTERN.match(kb_id_str):
        raise ValueError(f"Invalid kb_id format: {kb_id_str}")

    collection_name = f"{settings.MILVUS_COLLECTION_PREFIX}kb"
    alias = "cdm_cleanup"
    connections.connect(alias=alias, host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    try:
        col = Collection(collection_name, using=alias)
        # 构造组合查询表达式
        expr = f'kb_id == "{kb_id_str}" && filename == "{filename}"'
        col.load()
        results = col.query(expr=expr, output_fields=["pk"])
        count = len(results)
        if count > 0:
            col.delete(expr=expr)
        return count
    finally:
        connections.disconnect(alias)
