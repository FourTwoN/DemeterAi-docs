"""
Base Repository Pattern Template

This is a TEMPLATE file for creating AsyncRepository pattern.
DO NOT use directly - copy and customize for your project.

See: ../../00_foundation/architecture-principles.md
Card: R001-async-repository-base
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload, joinedload

# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType")


class AsyncRepository(Generic[ModelType]):
    """
    Base repository providing async CRUD operations for any SQLAlchemy model.

    Usage:
        class UserRepository(AsyncRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)

            async def get_by_email(self, email: str) -> Optional[User]:
                stmt = select(self.model).where(self.model.email == email)
                result = await self.session.execute(stmt)
                return result.scalar_one_or_none()
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository with model class and database session.

        Args:
            model: SQLAlchemy model class (e.g., User, StockMovement)
            session: Async database session (injected via FastAPI Depends)
        """
        self.model = model
        self.session = session

    async def get(self, id: Any) -> Optional[ModelType]:
        """
        Get single record by primary key.

        Args:
            id: Primary key value (int, UUID, str)

        Returns:
            Model instance or None if not found
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filters.

        Args:
            skip: Offset for pagination (default 0)
            limit: Max records to return (default 100)
            **filters: Column=value filters (e.g., status="active")

        Returns:
            List of model instances
        """
        stmt = select(self.model).filter_by(**filters).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create new record.

        Args:
            obj_in: Dictionary of column names and values

        Returns:
            Created model instance with ID populated
        """
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()  # Get ID without committing
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update existing record by ID.

        Args:
            id: Primary key value
            obj_in: Dictionary of columns to update

        Returns:
            Updated model instance or None if not found
        """
        db_obj = await self.get(id)
        if not db_obj:
            return None

        for field, value in obj_in.items():
            setattr(db_obj, field, value)

        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: Any) -> bool:
        """
        Delete record by ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get(id)
        if not db_obj:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def count(self, **filters) -> int:
        """
        Count records matching filters.

        Args:
            **filters: Column=value filters

        Returns:
            Count of matching records
        """
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def exists(self, id: Any) -> bool:
        """
        Check if record exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if exists, False otherwise
        """
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


# Example specialized repository
class StockMovementRepository(AsyncRepository["StockMovement"]):
    """
    Example specialized repository with custom query methods.

    TEMPLATE - Customize for your model's specific queries.
    """

    def __init__(self, session: AsyncSession):
        from app.models.stock_movement import StockMovement  # Import inside
        super().__init__(StockMovement, session)

    async def get_by_location(
        self,
        location_id: int,
        limit: int = 50
    ) -> List["StockMovement"]:
        """
        Get movements for a specific storage location.

        CRITICAL: Use eager loading to prevent N+1 queries!
        """
        stmt = (
            select(self.model)
            .where(self.model.storage_location_id == location_id)
            .options(
                joinedload(self.model.storage_location),  # Many-to-one
                selectinload(self.model.batch),           # Many-to-one
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())  # .unique() required with joinedload

    async def get_by_date_range(
        self,
        start_date: "datetime",
        end_date: "datetime"
    ) -> List["StockMovement"]:
        """Get movements within date range."""
        stmt = (
            select(self.model)
            .where(
                self.model.created_at >= start_date,
                self.model.created_at <= end_date
            )
            .order_by(self.model.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# Anti-Patterns to Avoid
class BAD_Repository_Examples:
    """
    DO NOT DO THESE THINGS!
    """

    # ❌ BAD: Business logic in repository
    async def calculate_total_stock(self):
        # Business logic belongs in Service layer, NOT repository
        pass

    # ❌ BAD: Calling other repositories directly
    async def get_movement_with_config(self, movement_id: int):
        # movement = await self.get(movement_id)
        # config_repo = StorageLocationConfigRepository(self.session)  # WRONG
        # config = await config_repo.get(movement.location_id)  # WRONG
        # return movement, config
        pass

    # ❌ BAD: Lazy loading in async (causes N+1 queries)
    async def get_all_with_locations(self):
        # stmt = select(self.model)  # No eager loading
        # result = await self.session.execute(stmt)
        # movements = result.scalars().all()
        # for m in movements:
        #     print(m.storage_location.name)  # +1 query per movement!
        pass


# Testing Example
"""
# tests/unit/repositories/test_stock_movement_repository.py
import pytest
from app.repositories.stock_movement_repository import StockMovementRepository

@pytest.mark.asyncio
async def test_get_by_location(db_session, stock_movement_factory):
    # Arrange
    repo = StockMovementRepository(db_session)
    movement = await stock_movement_factory.create(location_id=123)

    # Act
    results = await repo.get_by_location(location_id=123)

    # Assert
    assert len(results) == 1
    assert results[0].id == movement.id
"""
