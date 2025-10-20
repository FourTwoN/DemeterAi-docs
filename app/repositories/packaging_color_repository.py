"""Packaging color repository for color catalog data access.

Provides CRUD operations for packaging color entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_color import PackagingColor
from app.repositories.base import AsyncRepository


class PackagingColorRepository(AsyncRepository[PackagingColor]):
    """Repository for packaging color database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(PackagingColor, session)
