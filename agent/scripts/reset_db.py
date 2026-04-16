"""重置数据库：清空所有表和 RLS 策略，重建 public schema"""

import asyncio

from app.core.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def drop_all():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # 删除所有表（CASCADE 会一并清理外键、索引、RLS 等）
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        # 重新安装 pgvector 扩展
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await engine.dispose()
    print("数据库已清理完成：已重建 public schema 和 vector 扩展")


if __name__ == "__main__":
    asyncio.run(drop_all())
