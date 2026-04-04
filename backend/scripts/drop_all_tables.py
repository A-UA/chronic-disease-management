"""Drop 所有业务表，准备全量重建"""
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as db:
        # 先关闭外键约束检查
        await db.execute(text("SET session_replication_role = 'replica';"))

        # 获取所有业务表（排除 alembic_version）
        result = await db.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename != 'alembic_version'
        """))
        tables = [row[0] for row in result.fetchall()]

        for table in tables:
            await db.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            print(f"  Dropped: {table}")

        # 恢复外键检查
        await db.execute(text("SET session_replication_role = 'origin';"))
        await db.commit()
        print(f"\n[OK] Dropped {len(tables)} tables")


if __name__ == "__main__":
    asyncio.run(main())
