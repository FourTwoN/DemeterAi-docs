"""Storage location configuration repository for location config data access.

Provides CRUD operations for storage location configuration entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_location_config import StorageLocationConfig
from app.repositories.base import AsyncRepository


class StorageLocationConfigRepository(AsyncRepository[StorageLocationConfig]):
    """Repository for storage location config database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(StorageLocationConfig, session)
