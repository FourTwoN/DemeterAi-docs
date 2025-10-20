"""Packaging type repository for packaging type catalog data access.

Provides CRUD operations for packaging type entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_type import PackagingType
from app.repositories.base import AsyncRepository


class PackagingTypeRepository(AsyncRepository[PackagingType]):
    """Repository for packaging type database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(PackagingType, session)
