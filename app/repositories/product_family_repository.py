"""Product family repository for plant family taxonomy data access.

Provides CRUD operations for product family entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_family import ProductFamily
from app.repositories.base import AsyncRepository


class ProductFamilyRepository(AsyncRepository[ProductFamily]):
    """Repository for product family database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(ProductFamily, session)
