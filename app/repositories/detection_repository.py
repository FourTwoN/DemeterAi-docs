"""Detection repository for YOLO detection data access.

Provides CRUD operations for detection entities from ML pipeline.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection import Detection
from app.repositories.base import AsyncRepository


class DetectionRepository(AsyncRepository[Detection]):
    """Repository for detection database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Detection, session)
