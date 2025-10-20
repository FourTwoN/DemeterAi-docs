"""Stock batch repository for inventory batch data access.

Provides CRUD operations for stock batch entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_batch import StockBatch
from app.repositories.base import AsyncRepository


class StockBatchRepository(AsyncRepository[StockBatch]):
    """Repository for stock batch database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(StockBatch, session)
