from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.infrastructure.config import settings

engine = create_async_engine(settings.async_database_url, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
