"""Packaging material repository for material catalog data access.

Provides CRUD operations for packaging material entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_material import PackagingMaterial
from app.repositories.base import AsyncRepository


class PackagingMaterialRepository(AsyncRepository[PackagingMaterial]):
    """Repository for packaging material database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(PackagingMaterial, session)
