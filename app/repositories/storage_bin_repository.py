"""Storage bin repository for storage bin data access.

Provides CRUD operations for storage bin entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_bin import StorageBin
from app.repositories.base import AsyncRepository


class StorageBinRepository(AsyncRepository[StorageBin]):
    """Repository for storage bin database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(StorageBin, session)
