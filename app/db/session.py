"""Database session management with async SQLAlchemy.

This module provides async database connection management using SQLAlchemy 2.0
with connection pooling, health checks, and FastAPI dependency injection.

Key features:
- Async engine with asyncpg driver (350x faster bulk inserts than sync ORM)
- Connection pooling (pool_size=20, max_overflow=10)
- FastAPI dependency for automatic session lifecycle management
- Health check function for monitoring database connectivity
- Proper transaction management (auto-commit/rollback)
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create async engine with connection pooling
# asyncpg is 350× faster than psycopg2 for bulk operations
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO_SQL,  # Log SQL queries (DEBUG only)
    pool_size=settings.DB_POOL_SIZE,  # Base connection pool size
    max_overflow=settings.DB_MAX_OVERFLOW,  # Emergency connections
    pool_pre_ping=True,  # Verify connection health before use
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Async session factory for creating database sessions
# expire_on_commit=False keeps objects in memory after commit (prevents N+1 queries)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects accessible after commit
    autocommit=False,  # Explicit transaction control
    autoflush=False,  # Manual flush control for better performance
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Provides automatic session lifecycle management:
    - Creates new session for each request
    - Commits transaction on successful completion
    - Rolls back on exception
    - Always closes session (even on error)

    Usage:
        @router.get("/warehouses")
        async def get_warehouses(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Warehouse))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session for the request lifecycle
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_connection() -> bool:
    """Test database connectivity for health checks.

    Executes a simple SELECT 1 query to verify the database is reachable
    and responding. Used by health check endpoints.

    Returns:
        bool: True if connection successful, False otherwise

    Example:
        if await test_connection():
            logger.info("Database is healthy")
        else:
            logger.error("Database connection failed")
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(
            "Database connection test failed",
            error=str(e),
            exc_info=True,
        )
        return False


async def close_db_connection() -> None:
    """Close all database connections gracefully.

    Should be called during application shutdown to ensure all connections
    are properly released back to PostgreSQL.

    Usage:
        @app.on_event("shutdown")
        async def shutdown_event():
            await close_db_connection()
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(
            "Error closing database connections",
            error=str(e),
            exc_info=True,
        )
