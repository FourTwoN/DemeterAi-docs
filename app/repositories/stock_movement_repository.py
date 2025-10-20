"""Stock movement repository for inventory movement data access.

Provides CRUD operations for stock movement entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_movement import StockMovement
from app.repositories.base import AsyncRepository


class StockMovementRepository(AsyncRepository[StockMovement]):
    """Repository for stock movement database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(StockMovement, session)
