"""
Async SQLAlchemy engine/session setup.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# pool_size/max_overflow only apply to pool-backed dialects (asyncpg in
# production). SQLite (used for lightweight local testing) uses NullPool
# and rejects those kwargs outright, so they're only passed for Postgres.
_engine_kwargs = {"pool_pre_ping": True}
if settings.database_url.startswith("postgresql"):
    _engine_kwargs.update(pool_size=10, max_overflow=10)

engine = create_async_engine(settings.database_url, **_engine_kwargs)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


def get_insert_stmt(model):
    """Return dialect-aware insert statement (supports both SQLite and PostgreSQL ON CONFLICT)."""
    if engine.url.drivername.startswith("sqlite"):
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        return sqlite_insert(model)
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    return pg_insert(model)


async def init_db() -> None:
    """Create all tables if they don't exist and run light schema upgrades."""
    from app import models  # noqa: F401  (ensure models are registered)
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe auto-migration for target_date column on existing SQLite DBs
        try:
            await conn.execute(text("ALTER TABLE predictions ADD COLUMN target_date VARCHAR(16)"))
        except Exception:
            pass  # column already exists


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
