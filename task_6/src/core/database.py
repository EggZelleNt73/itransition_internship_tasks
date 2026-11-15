from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from src.core.config import settings


async_engine = create_async_engine(
    url=settings.database_url,
    pool_size=5,
    max_overflow=15,
    pool_pre_ping=True
)


async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


if __name__ == "__main__":
    pass