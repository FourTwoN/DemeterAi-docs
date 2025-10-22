"""Generic async repository pattern for DemeterAI v2.0.

This module provides a base repository class implementing the Repository Pattern
with SQLAlchemy 2.0 async API. All specialized repositories inherit from this base.

Design Principles:
- Generic programming: TypeVar[T] for type safety across all models
- Async-first: All methods use async/await with AsyncSession
- Clean Architecture: Repository only does data access (no business logic)
- Transaction management: flush() + refresh() pattern (caller controls commit)

Architecture:
    Layer: Infrastructure (Repository Pattern)
    Dependencies: SQLAlchemy 2.0.43, Python 3.12
    Usage: Inherited by all specialized repositories (R001-R026, R028)

Example:
    ```python
    from app.repositories.base import AsyncRepository
    from app.models.warehouse import Warehouse
    from sqlalchemy.ext.asyncio import AsyncSession

    class WarehouseRepository(AsyncRepository[Warehouse]):
        def __init__(self, session: AsyncSession):
            super().__init__(Warehouse, session)

        async def get_by_code(self, code: str) -> Warehouse | None:
            stmt = select(self.model).where(self.model.code == code)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
    ```

See:
    - engineering_plan/03_architecture_overview.md (Repository Pattern)
    - backlog/04_templates/starter-code/base_repository.py (template)
"""

from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

# Generic type variable bound to SQLAlchemy Base
# This allows AsyncRepository to work with any SQLAlchemy model
T = TypeVar("T", bound=Base)


class AsyncRepository[T: Base]:
    """Generic async repository providing CRUD operations for any SQLAlchemy model.

    This base class implements common database operations using SQLAlchemy 2.0
    async API. All specialized repositories inherit from this class and can add
    custom query methods as needed.

    Key Features:
    - Generic type parameter T for type safety
    - Async/await for non-blocking database I/O
    - Transaction management with flush() + refresh()
    - Pagination support with skip/limit
    - Filter support with **kwargs
    - No auto-commit (caller controls transaction boundaries)

    Attributes:
        model: SQLAlchemy model class (e.g., Warehouse, Product)
        session: Async database session (injected via FastAPI Depends)

    Note:
        This class does NOT commit transactions automatically. Use flush()
        to get IDs and maintain transaction isolation. The caller (typically
        a service layer) is responsible for committing or rolling back.
    """

    def __init__(self, model: type[T], session: AsyncSession) -> None:
        """Initialize repository with model class and database session.

        Args:
            model: SQLAlchemy model class (e.g., Warehouse, StockMovement)
            session: Async database session (injected via FastAPI Depends)

        Example:
            ```python
            # In specialized repository
            class WarehouseRepository(AsyncRepository[Warehouse]):
                def __init__(self, session: AsyncSession):
                    super().__init__(Warehouse, session)
            ```
        """
        self.model = model
        self.session = session

    async def get(self, id: Any) -> T | None:
        """Get single record by primary key.

        Performs indexed lookup by primary key (typically very fast, <10ms).
        Returns None if record not found (does not raise exception).

        Args:
            id: Primary key value (int, UUID, str depending on model)

        Returns:
            Model instance if found, None otherwise

        Example:
            ```python
            warehouse = await repo.get(123)
            if warehouse:
                # warehouse.name
            ```
        """
        stmt = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100, **filters: Any) -> list[T]:
        """Get multiple records with pagination and optional filters.

        Supports standard pagination with skip/limit and keyword filters.
        Use specialized repository methods for complex queries with joins.

        Args:
            skip: Number of records to skip (default: 0)
            limit: Maximum records to return (default: 100)
            **filters: Column=value filters (e.g., active=True, type="greenhouse")

        Returns:
            List of model instances (empty list if no matches)

        Example:
            ```python
            # Get first 10 active warehouses
            warehouses = await repo.get_multi(skip=0, limit=10, active=True)

            # Get second page
            warehouses = await repo.get_multi(skip=10, limit=10, active=True)
            ```

        Note:
            For complex queries with joins, create custom methods in
            specialized repository (e.g., get_with_locations()).
        """
        stmt = select(self.model).filter_by(**filters).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> T:
        """Create new record in database.

        Uses flush() + refresh() pattern to get auto-generated ID and load
        relationships WITHOUT committing the transaction. Caller controls commit.

        Args:
            obj_in: Dictionary of column names and values

        Returns:
            Created model instance with ID populated and relationships loaded

        Raises:
            sqlalchemy.exc.IntegrityError: If constraints violated (duplicate key, etc.)

        Example:
            ```python
            warehouse = await repo.create({
                "code": "WH-001",
                "name": "Main Warehouse",
                "type": "greenhouse",
                "active": True
            })
            # Created with ID: {warehouse.id}
            ```

        Note:
            This method does NOT commit. The session must be committed
            by the caller (typically in service layer or endpoint).
        """
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()  # Write to DB, get ID, stay in transaction
        await self.session.refresh(db_obj)  # Load relationships and defaults
        return db_obj

    async def update(self, id: Any, obj_in: dict[str, Any]) -> T | None:
        """Update existing record by ID.

        Supports partial updates (only provided fields are modified).
        Uses flush() + refresh() to maintain transaction isolation.

        Args:
            id: Primary key value
            obj_in: Dictionary of columns to update (partial update supported)

        Returns:
            Updated model instance if found, None if ID not found

        Example:
            ```python
            # Partial update (only name)
            warehouse = await repo.update(123, {"name": "New Name"})

            # Multiple fields
            warehouse = await repo.update(123, {
                "name": "New Name",
                "active": False,
                "description": "Updated description"
            })
            ```

        Note:
            Does NOT commit. Caller controls transaction boundaries.
        """
        db_obj = await self.get(id)
        if not db_obj:
            return None

        # Apply partial update
        for field, value in obj_in.items():
            setattr(db_obj, field, value)

        await self.session.flush()  # Write changes to DB
        await self.session.refresh(db_obj)  # Reload to get updated timestamps
        return db_obj

    async def delete(self, id: Any) -> bool:
        """Delete record by ID.

        Performs hard delete (removes from database). For soft deletes,
        use update() to set active=False or deleted_at=now().

        Args:
            id: Primary key value

        Returns:
            True if record was deleted, False if ID not found

        Example:
            ```python
            success = await repo.delete(123)
            if success:
                # Warehouse deleted
            else:
                # Warehouse not found
            ```

        Note:
            This is a HARD delete. Consider soft deletes for audit trails.
            Does NOT commit - caller controls transaction boundaries.
        """
        db_obj = await self.get(id)
        if not db_obj:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def count(self, **filters: Any) -> int:
        """Count records matching optional filters.

        Uses SQL COUNT aggregate for efficiency (does not load records).
        Useful for pagination metadata and dashboards.

        Args:
            **filters: Column=value filters (same as get_multi)

        Returns:
            Count of matching records

        Example:
            ```python
            # Count all warehouses
            total = await repo.count()

            # Count active warehouses
            active_count = await repo.count(active=True)

            # Pagination metadata
            total = await repo.count(active=True)
            pages = (total + limit - 1) // limit
            ```

        Performance:
            ~30ms typical (COUNT aggregate is fast with proper indexes)
        """
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, id: Any) -> bool:
        """Check if record exists by ID without loading full object.

        More efficient than get() when you only need existence check.
        Only queries the ID column (not all columns).

        Args:
            id: Primary key value

        Returns:
            True if record exists, False otherwise

        Example:
            ```python
            if await repo.exists(123):
                # Warehouse exists
            else:
                # Warehouse not found
            ```

        Performance:
            ~5ms typical (indexed PK lookup, no object hydration)
        """
        stmt = select(self.model.id).where(self.model.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
