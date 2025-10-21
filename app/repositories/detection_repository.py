"""Detection repository for YOLO detection data access.

Provides CRUD operations for detection entities from ML pipeline.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection import Detection
from app.repositories.base import AsyncRepository


class DetectionRepository(AsyncRepository[Detection]):
    """Repository for detection database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Detection, session)

    async def get_by_session(self, session_id: int, limit: int = 1000) -> list[Detection]:
        """Get all detections for a photo processing session.

        Args:
            session_id: Photo processing session ID
            limit: Max results (default 1000)

        Returns:
            List of Detection ordered by created_at DESC
        """
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, detections: list[dict[str, Any]]) -> list[Detection]:
        """Bulk create detections (optimized for performance).

        Args:
            detections: List of detection dicts

        Returns:
            List of created Detection instances

        Note:
            Uses bulk_insert_mappings for performance with large datasets.
            All detections are flushed and refreshed to get IDs.
        """
        # Create detection instances
        db_detections = [Detection(**data) for data in detections]

        # Add all to session
        self.session.add_all(db_detections)
        await self.session.flush()

        # Refresh all to get IDs and computed columns
        for detection in db_detections:
            await self.session.refresh(detection)

        return db_detections
