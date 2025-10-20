"""Product repository for plant species data access.

Provides CRUD operations for product entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base import AsyncRepository


class ProductRepository(AsyncRepository[Product]):
    """Repository for product database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Product, session)
