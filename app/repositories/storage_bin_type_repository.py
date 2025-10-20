"""Storage bin type repository for bin type catalog data access.

Provides CRUD operations for storage bin type entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_bin_type import StorageBinType
from app.repositories.base import AsyncRepository


class StorageBinTypeRepository(AsyncRepository[StorageBinType]):
    """Repository for storage bin type database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(StorageBinType, session)
