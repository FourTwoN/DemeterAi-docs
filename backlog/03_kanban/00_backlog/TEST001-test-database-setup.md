# [TEST001] Test Database Setup

## Metadata
- **Epic**: epic-012-testing
- **Sprint**: Sprint-02
- **Priority**: `critical` ⚡
- **Complexity**: M (5 points)
- **Dependencies**: Blocks [TEST002-TEST015], Blocked by [F006, F009]

## Description
Configure pytest with test database: isolated PostgreSQL instance, automatic schema creation/teardown, transaction rollback per test.

## Acceptance Criteria
- [ ] Test database URL in .env.test
- [ ] Pytest fixture creates fresh database for each test session
- [ ] Each test runs in transaction (auto-rollback)
- [ ] Alembic migrations applied to test DB
- [ ] Parallel test execution supported (pytest-xdist)

## Implementation
**conftest.py:**
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.core.config import settings

@pytest.fixture(scope="session")
async def test_db_engine():
    engine = create_async_engine(settings.TEST_DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
async def db_session(test_db_engine):
    SessionLocal = sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with SessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()  # Rollback after each test
```

## Testing
- Run: `pytest tests/`
- Verify test DB created and destroyed
- Verify tests isolated (no data leakage)

---
**Card Created**: 2025-10-09
