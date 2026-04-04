"""清理 alembic_version 表，准备全新迁移"""
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM alembic_version"))
        await db.commit()
        print("[OK] alembic_version cleared")


if __name__ == "__main__":
    asyncio.run(main())
