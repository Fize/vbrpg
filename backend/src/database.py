"""Database configuration and session management."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from src.utils.config import settings

# Create async engine with SQLite
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    poolclass=NullPool,  # SQLite doesn't support connection pooling well
    connect_args={"check_same_thread": False},
)

# Configure async session
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database with WAL mode and foreign keys."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Enable WAL mode for better concurrency
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        # Enable foreign key constraints
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        # Increase cache size (64MB)
        await conn.execute(text("PRAGMA cache_size=-64000"))
