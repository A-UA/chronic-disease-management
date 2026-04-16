"""Milvus 向量数据库客户端实现"""

from __future__ import annotations

import logging
from typing import Any

from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient

logger = logging.getLogger(__name__)


class MilvusVectorStore:
    """Milvus 向量数据库封装，实现 VectorStoreProtocol"""

    def __init__(self, host: str, port: int, collection_prefix: str = "cdm"):
        self._client = MilvusClient(uri=f"http://{host}:{port}")
        self._prefix = collection_prefix

    def _full_name(self, name: str) -> str:
        return f"{self._prefix}_{name}"

    async def ensure_collection(self, collection_name: str, dimension: int) -> None:
        """确保 collection 存在"""
        full_name = self._full_name(collection_name)
        if self._client.has_collection(full_name):
            return

        schema = CollectionSchema(
            fields=[
                FieldSchema(
                    name="id", dtype=DataType.INT64, is_primary=True, auto_id=True
                ),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="document_id", dtype=DataType.INT64),
                FieldSchema(name="chunk_index", dtype=DataType.INT32),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="page_number", dtype=DataType.INT32),
                FieldSchema(name="token_count", dtype=DataType.INT32),
                FieldSchema(
                    name="section_title", dtype=DataType.VARCHAR, max_length=512
                ),
                FieldSchema(name="tenant_id", dtype=DataType.INT64),
                FieldSchema(name="kb_id", dtype=DataType.INT64),
            ]
        )
        self._client.create_collection(
            collection_name=full_name,
            schema=schema,
        )
        # 创建向量索引
        self._client.create_index(
            collection_name=full_name,
            field_name="vector",
            index_params={
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128},
            },
        )
        # 创建 document_id 标量索引（用于删除）
        self._client.create_index(
            collection_name=full_name,
            field_name="document_id",
        )
        logger.info("Created Milvus collection: %s (dim=%d)", full_name, dimension)

    async def insert(
        self,
        collection_name: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> int:
        """插入向量+元数据"""
        full_name = self._full_name(collection_name)
        data = []
        for vec, payload in zip(vectors, payloads):
            row = {"vector": vec, **payload}
            data.append(row)

        result = self._client.insert(collection_name=full_name, data=data)
        count = result.get("insert_count", len(vectors))
        return count

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """向量检索"""
        full_name = self._full_name(collection_name)
        filter_expr = ""
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, int):
                    conditions.append(f"{key} == {value}")
                elif isinstance(value, list):
                    conditions.append(f"{key} in {value}")
            filter_expr = " and ".join(conditions)

        results = self._client.search(
            collection_name=full_name,
            data=[vector],
            limit=limit,
            filter=filter_expr if filter_expr else None,
            output_fields=[
                "document_id",
                "content",
                "chunk_index",
                "page_number",
                "token_count",
                "section_title",
                "tenant_id",
                "kb_id",
            ],
        )

        parsed = []
        for hits in results:
            for hit in hits:
                parsed.append(
                    {
                        "id": hit["id"],
                        "score": hit["distance"],
                        "payload": hit["entity"],
                    }
                )
        return parsed

    async def delete_by_document_id(
        self,
        collection_name: str,
        document_id: int,
    ) -> int:
        """按 document_id 删除所有切块"""
        full_name = self._full_name(collection_name)
        result = self._client.delete(
            collection_name=full_name,
            filter=f"document_id == {document_id}",
        )
        return result.get("delete_count", 0)
