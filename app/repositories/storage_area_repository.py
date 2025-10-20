"""Storage area repository for geospatial storage area data access.

Provides CRUD operations for storage area entities with PostGIS support.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_area import StorageArea
from app.repositories.base import AsyncRepository


class StorageAreaRepository(AsyncRepository[StorageArea]):
    """Repository for storage area database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(StorageArea, session)
