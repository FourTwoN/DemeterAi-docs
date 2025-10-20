"""Storage location repository for geospatial storage location data access.

Provides CRUD operations for storage location entities with PostGIS support.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_location import StorageLocation
from app.repositories.base import AsyncRepository


class StorageLocationRepository(AsyncRepository[StorageLocation]):
    """Repository for storage location database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(StorageLocation, session)
