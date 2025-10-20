"""Price list repository for pricing catalog data access.

Provides CRUD operations for price list entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_list import PriceList
from app.repositories.base import AsyncRepository


class PriceListRepository(AsyncRepository[PriceList]):
    """Repository for price list database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(PriceList, session)
