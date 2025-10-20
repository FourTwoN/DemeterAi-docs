"""Packaging catalog repository for complete packaging SKU data access.

Provides CRUD operations for packaging catalog entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_catalog import PackagingCatalog
from app.repositories.base import AsyncRepository


class PackagingCatalogRepository(AsyncRepository[PackagingCatalog]):
    """Repository for packaging catalog database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(PackagingCatalog, session)
