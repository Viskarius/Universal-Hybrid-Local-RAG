from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.db.models import Base


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_maker(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_hash TEXT")
        )
        await conn.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash TEXT")
        )
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS documents_file_hash_key "
                "ON documents (file_hash)"
            )
        )
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS documents_content_hash_key "
                "ON documents (content_hash)"
            )
        )
