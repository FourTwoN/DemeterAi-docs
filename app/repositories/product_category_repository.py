"""Product category repository for product taxonomy data access.

Provides CRUD operations for product category entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_category import ProductCategory
from app.repositories.base import AsyncRepository


class ProductCategoryRepository(AsyncRepository[ProductCategory]):
    """Repository for product category database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(ProductCategory, session)
