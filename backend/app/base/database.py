from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.base.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG_SQL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
