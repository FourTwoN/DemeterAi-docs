"""Photo processing session repository for ML session data access.

Provides CRUD operations for photo processing session entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo_processing_session import PhotoProcessingSession
from app.repositories.base import AsyncRepository


class PhotoProcessingSessionRepository(AsyncRepository[PhotoProcessingSession]):
    """Repository for photo processing session database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(PhotoProcessingSession, session)
