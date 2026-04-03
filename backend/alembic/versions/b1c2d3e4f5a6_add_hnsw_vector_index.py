"""add_hnsw_vector_index_to_chunks

Revision ID: b1c2d3e4f5a6
Revises: a92280d61859
Create Date: 2026-04-03 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a92280d61859'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 chunks 表的 embedding 列创建 HNSW 向量索引。

    这是影响检索性能的最关键优化：无索引时向量检索为全表扫描，
    HNSW 索引可将检索从 O(N) 降至 O(log N)。

    参数说明：
    - m=16: 每个节点的最大连接数，越大精度越高但内存开销越大
    - ef_construction=64: 构建时的搜索宽度，越大索引质量越高但构建越慢
    - vector_cosine_ops: 使用余弦距离（与检索代码中 cosine_distance 一致）
    """
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
        ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)


def downgrade() -> None:
    """删除 HNSW 向量索引"""
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw;")
