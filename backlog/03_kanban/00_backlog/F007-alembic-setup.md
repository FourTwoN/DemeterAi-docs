# [F007] Alembic Setup - Database Migrations

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (5 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB001-DB035 (all model creation cards)]
  - Blocked by: [F001, F002, F006]

## Related Documentation
- **Database Migration Guide**: ../../engineering_plan/database/README.md#migration-strategy
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md#database-layer

## Description

Initialize Alembic for database schema migrations, configure for SQLAlchemy 2.0 async models, and create first migration with baseline schema.

**What**: Set up Alembic 1.14.0 with PostgreSQL 18, configure `alembic.ini` and `env.py` to work with async SQLAlchemy models, create initial migration with PostGIS extension enabled.

**Why**: Database schema changes must be versioned and reversible. Alembic provides migration history, rollback capability, and team synchronization. Without migrations, schema changes break local dev environments.

**Context**: DemeterAI has 28 tables with complex relationships. Manual SQL schema changes lead to inconsistencies. Alembic autogenerate detects model changes but requires manual review (not perfect).

## Acceptance Criteria

- [ ] **AC1**: Alembic initialized:
  ```bash
  alembic init alembic
  # Creates: alembic/, alembic.ini, alembic/env.py, alembic/versions/
  ```

- [ ] **AC2**: `alembic.ini` configured with PostgreSQL connection:
  ```ini
  sqlalchemy.url = postgresql+psycopg2://user:pass@localhost:5432/demeterai
  # Uses DATABASE_URL_SYNC (psycopg2, not asyncpg)
  ```

- [ ] **AC3**: `alembic/env.py` configured for SQLAlchemy 2.0:
  - Imports all models from `app.models`
  - Uses `Base.metadata` for autogenerate
  - Runs migrations in transaction
  - Supports both online and offline modes

- [ ] **AC4**: Initial migration created:
  ```bash
  alembic revision --autogenerate -m "initial schema with postgis"
  # Creates: alembic/versions/001_initial_schema_with_postgis.py
  ```

- [ ] **AC5**: Migration includes PostGIS extension:
  ```python
  def upgrade():
      op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
      # ... table creation
  ```

- [ ] **AC6**: Migrations work in both directions:
  ```bash
  alembic upgrade head  # Apply all migrations
  alembic downgrade -1  # Rollback one migration
  alembic current       # Show current version
  alembic history       # Show all migrations
  ```

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Database Infrastructure)
- Dependencies: Alembic 1.14.0, psycopg2-binary 2.9.10, SQLAlchemy models (Sprint 01)
- Design pattern: Database schema versioning

### Code Hints

**alembic/env.py structure:**
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import Base and all models
from app.db.base import Base  # Imports all models
from app.core.config import settings

# Alembic Config
config = context.config

# Override sqlalchemy.url from environment
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode (no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode (with DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**app/db/base.py (for model imports):**
```python
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here (for Alembic autogenerate)
from app.models.warehouse import Warehouse
from app.models.storage_area import StorageArea
# ... all models
```

**alembic/versions/001_initial_schema.py (example):**
```python
"""initial schema with postgis

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-10-09 14:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable PostGIS extension
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')

    # Create warehouses table
    op.create_table('warehouses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('geojson_coordinates', sa.Geometry('POLYGON'), nullable=True),
        sa.Column('active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    # ... more tables


def downgrade():
    op.drop_table('warehouses')
    # ... drop all tables
    op.execute('DROP EXTENSION IF EXISTS postgis')
```

### Testing Requirements

**Unit Tests**: N/A (infrastructure card)

**Integration Tests**:
- [ ] Test migration creation:
  ```bash
  alembic revision --autogenerate -m "test migration"
  # Verify file created in alembic/versions/
  ```

- [ ] Test upgrade/downgrade:
  ```bash
  alembic upgrade head
  psql -d demeterai -c "\dt"  # Verify tables exist

  alembic downgrade -1
  # Verify tables dropped
  ```

- [ ] Test PostGIS extension:
  ```bash
  alembic upgrade head
  psql -d demeterai -c "SELECT PostGIS_Version();"
  # Expected: PostGIS 3.3+ version string
  ```

**Test Command**:
```bash
# Test migration workflow
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

### Performance Expectations
- Migration generation: <5 seconds
- Migration execution (initial): <10 seconds
- Rollback: <5 seconds

## Handover Briefing

**For the next developer:**
- **Context**: This is the foundation for database schema evolution - all model changes go through Alembic
- **Key decisions**:
  - Using psycopg2 for migrations (asyncpg not supported by Alembic)
  - Autogenerate enabled BUT manual review required (Alembic misses some changes)
  - PostGIS extension in first migration (enables geometry columns)
  - Transactions enabled (migrations can rollback on error)
  - Environment variable override (DATABASE_URL_SYNC from .env)
- **Known limitations**:
  - Alembic doesn't detect all changes (e.g., server defaults, check constraints)
  - Manual migrations needed for data migrations
  - PostGIS indexes not auto-generated (manual creation required)
- **Next steps after this card**:
  - DB001-DB035: Create SQLAlchemy models
  - After each model: `alembic revision --autogenerate -m "add XXX table"`
  - Review generated migration before applying
- **Questions to ask**:
  - Should we use Alembic branching for hotfixes? (production schema changes)
  - Should we automate migrations in CI/CD? (Sprint 05)
  - Should we add migration testing in CI? (verify upgrade/downgrade works)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] Alembic initialized successfully
- [ ] Initial migration created and tested
- [ ] PostGIS extension enabled
- [ ] Upgrade/downgrade cycle works
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with migration commands)
- [ ] .env.example includes DATABASE_URL_SYNC

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
