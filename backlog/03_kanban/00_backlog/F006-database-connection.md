# [F006] Database Connection Manager - Async Session + Pooling

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (5 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [F007, DB001-DB035, R001-R028]
  - Blocked by: [F001, F002]

## Related Documentation
- **Database Architecture**: ../../engineering_plan/database/README.md
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md#database-layer
- **Architecture**: ../../engineering_plan/03_architecture_overview.md#system-layers

## Description

Implement async database connection manager with SQLAlchemy 2.0.43 + asyncpg, connection pooling, and FastAPI dependency injection for database sessions.

**What**: Create `app/db/session.py` with async engine, session factory, and `get_db_session()` dependency for FastAPI. Configure connection pooling (pool_size=20, max_overflow=10) and proper session lifecycle management.

**Why**: Async database operations prevent FastAPI event loop blocking. Connection pooling prevents database connection exhaustion (PostgreSQL default: 100 max connections). Dependency injection ensures sessions are properly closed after each request.

**Context**: DemeterAI uses PostgreSQL 18 with PostGIS as single source of truth. All repositories depend on async sessions. Without proper pooling, 200+ concurrent requests would exhaust database connections.

## Acceptance Criteria

- [ ] **AC1**: `app/db/session.py` created with async engine:
  ```python
  engine = create_async_engine(
      DATABASE_URL,
      echo=False,  # SQL logging (DEBUG only)
      pool_size=20,  # Base pool
      max_overflow=10,  # Emergency connections
      pool_pre_ping=True,  # Test connections before use
      pool_recycle=3600  # Recycle after 1 hour
  )
  ```

- [ ] **AC2**: Async session factory:
  ```python
  AsyncSessionLocal = async_sessionmaker(
      engine,
      class_=AsyncSession,
      expire_on_commit=False,  # Keep objects after commit
      autocommit=False,
      autoflush=False
  )
  ```

- [ ] **AC3**: FastAPI dependency for database sessions:
  ```python
  async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
      async with AsyncSessionLocal() as session:
          try:
              yield session
              await session.commit()
          except Exception:
              await session.rollback()
              raise
          finally:
              await session.close()
  ```

- [ ] **AC4**: Environment variable configuration:
  - `DATABASE_URL`: postgresql+asyncpg://user:pass@host:5432/db
  - `DATABASE_URL_SYNC`: postgresql+psycopg2://... (for Alembic migrations)
  - `DB_POOL_SIZE`: 20
  - `DB_MAX_OVERFLOW`: 10
  - `DB_ECHO_SQL`: false (true for debugging)

- [ ] **AC5**: Connection test function:
  ```python
  async def test_connection() -> bool:
      """Test database connectivity."""
      try:
          async with engine.begin() as conn:
              await conn.execute(text("SELECT 1"))
          return True
      except Exception as e:
          logger.error("Database connection failed", error=str(e))
          return False
  ```

- [ ] **AC6**: Usage in FastAPI controllers:
  ```python
  @router.get("/health")
  async def health(session: AsyncSession = Depends(get_db_session)):
      # Session auto-injected, auto-closed
      result = await session.execute(select(Warehouse))
      return {"status": "healthy"}
  ```

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Database Infrastructure)
- Dependencies: SQLAlchemy 2.0.43, asyncpg 0.30.0, PostgreSQL 18
- Design pattern: Dependency injection, connection pooling, unit of work

### Code Hints

**app/db/session.py structure:**
```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy import text
from typing import AsyncGenerator
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Async engine for application (asyncpg)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO_SQL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connection health
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(Item))
            return result.scalars().all()
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
    """Test database connectivity (for health checks)."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e), exc_info=True)
        return False
```

**app/core/config.py (settings):**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str  # postgresql+asyncpg://...
    DATABASE_URL_SYNC: str  # postgresql+psycopg2://... (for Alembic)
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO_SQL: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

**.env.example:**
```env
DATABASE_URL=postgresql+asyncpg://demeter:password@localhost:5432/demeterai
DATABASE_URL_SYNC=postgresql+psycopg2://demeter:password@localhost:5432/demeterai
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_ECHO_SQL=false
```

### Testing Requirements

**Unit Tests**:
- [ ] Test engine creation:
  ```python
  def test_engine_configuration():
      assert engine.pool.size() == 20
      assert engine.pool._max_overflow == 10
  ```

- [ ] Test session factory:
  ```python
  @pytest.mark.asyncio
  async def test_session_factory():
      async with AsyncSessionLocal() as session:
          assert isinstance(session, AsyncSession)
          result = await session.execute(text("SELECT 1"))
          assert result.scalar() == 1
  ```

**Integration Tests**:
- [ ] Test database connectivity:
  ```python
  @pytest.mark.asyncio
  async def test_database_connection():
      connected = await test_connection()
      assert connected is True
  ```

- [ ] Test FastAPI dependency injection:
  ```python
  @pytest.mark.asyncio
  async def test_get_db_session_dependency(client):
      response = await client.get("/health")
      assert response.status_code == 200
  ```

- [ ] Test session auto-rollback on error:
  ```python
  @pytest.mark.asyncio
  async def test_session_rollback_on_error():
      async with AsyncSessionLocal() as session:
          try:
              await session.execute(text("INVALID SQL"))
          except Exception:
              # Session should auto-rollback
              pass
          # Verify no hanging transaction
  ```

**Test Command**:
```bash
pytest tests/db/test_session.py -v --cov=app/db/session
```

### Performance Expectations
- Connection acquisition: <5ms (from pool)
- Session creation: <2ms
- Connection test (SELECT 1): <1ms
- Pool exhaustion handling: Blocks until connection available (max 30s timeout)

## Handover Briefing

**For the next developer:**
- **Context**: This is the foundation for ALL database access - every repository uses these sessions
- **Key decisions**:
  - Using asyncpg (350× faster bulk inserts than ORM)
  - Pool size 20 + overflow 10 = 30 max connections (conservative for 100 PostgreSQL limit)
  - `expire_on_commit=False`: Keep objects in memory after commit (prevents N+1 queries)
  - `pool_pre_ping=True`: Prevents "connection lost" errors
  - Two DATABASE_URLs: asyncpg (app) + psycopg2 (Alembic migrations - can't use async)
- **Known limitations**:
  - Alembic migrations use sync psycopg2 (asyncpg not supported in Alembic)
  - Connection pool shared across all API workers (need PgBouncer for production)
  - No connection encryption yet (add SSL in production)
- **Next steps after this card**:
  - F007: Alembic setup (uses DATABASE_URL_SYNC)
  - DB001-DB035: SQLAlchemy models (use engine)
  - R001-R028: Repositories (use get_db_session dependency)
- **Questions to ask**:
  - Should we use PgBouncer for production? (recommended for >100 API workers)
  - Should we enable SSL for database connections? (required for AWS RDS)
  - Should we add read replicas for analytics queries? (Sprint 05 decision)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] Database connection works (test_connection() succeeds)
- [ ] FastAPI dependency injection works
- [ ] Connection pooling configured
- [ ] Environment variables documented in .env.example
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with database setup instructions)
- [ ] No raw database credentials in code (all in .env)

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
