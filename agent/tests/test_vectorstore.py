from unittest.mock import MagicMock, patch

import pytest


class FakeMilvusResult:
    """模拟 Milvus 搜索结果"""

    def __init__(self, hits):
        self._hits = hits

    def __iter__(self):
        return iter(self._hits)

    def __len__(self):
        return len(self._hits)


class FakeHit:
    def __init__(self, id, distance, entity):
        self.id = id
        self.distance = distance
        self.entity = entity


@pytest.mark.asyncio
async def test_milvus_insert_vectors():
    """测试向量插入时正确调用 Milvus insert"""
    with patch("app.vectorstore.milvus.MilvusClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.insert.return_value = {"insert_count": 2}

        from app.vectorstore.milvus import MilvusVectorStore

        store = MilvusVectorStore(
            host="localhost", port=19530, collection_prefix="test"
        )

        result = await store.insert(
            collection_name="test_kb_1",
            vectors=[[0.1, 0.2], [0.3, 0.4]],
            payloads=[
                {"document_id": 1, "content": "测试内容1", "chunk_index": 0},
                {"document_id": 1, "content": "测试内容2", "chunk_index": 1},
            ],
        )
        assert result == 2
        mock_client.insert.assert_called_once()


@pytest.mark.asyncio
async def test_milvus_search():
    """测试向量搜索返回正确结构"""
    with patch("app.vectorstore.milvus.MilvusClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client

        mock_client.search.return_value = [
            [
                {
                    "id": 1,
                    "distance": 0.95,
                    "entity": {"content": "结果1", "document_id": 10},
                },
                {
                    "id": 2,
                    "distance": 0.80,
                    "entity": {"content": "结果2", "document_id": 10},
                },
            ]
        ]

        from app.vectorstore.milvus import MilvusVectorStore

        store = MilvusVectorStore(
            host="localhost", port=19530, collection_prefix="test"
        )

        results = await store.search(
            collection_name="test_kb_1",
            vector=[0.1, 0.2],
            limit=5,
        )
        assert len(results) == 2
        assert results[0]["score"] == 0.95
        assert results[0]["payload"]["content"] == "结果1"


@pytest.mark.asyncio
async def test_milvus_delete_by_document_id():
    """测试按 document_id 删除切块"""
    with patch("app.vectorstore.milvus.MilvusClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.delete.return_value = {"delete_count": 5}

        from app.vectorstore.milvus import MilvusVectorStore

        store = MilvusVectorStore(
            host="localhost", port=19530, collection_prefix="test"
        )

        count = await store.delete_by_document_id(
            collection_name="test_kb_1",
            document_id=123,
        )
        assert count == 5
