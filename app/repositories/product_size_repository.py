"""Product size repository for plant size catalog data access.

Provides CRUD operations for product size entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_size import ProductSize
from app.repositories.base import AsyncRepository


class ProductSizeRepository(AsyncRepository[ProductSize]):
    """Repository for product size database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(ProductSize, session)
