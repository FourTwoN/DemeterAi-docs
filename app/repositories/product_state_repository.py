"""Product state repository for plant lifecycle state data access.

Provides CRUD operations for product state entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_state import ProductState
from app.repositories.base import AsyncRepository


class ProductStateRepository(AsyncRepository[ProductState]):
    """Repository for product state database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(ProductState, session)
