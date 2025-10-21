"""Photo processing session repository for ML session data access.

Provides CRUD operations for photo processing session entities.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo_processing_session import (
    PhotoProcessingSession,
    ProcessingSessionStatusEnum,
)
from app.repositories.base import AsyncRepository


class PhotoProcessingSessionRepository(AsyncRepository[PhotoProcessingSession]):
    """Repository for photo processing session database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(PhotoProcessingSession, session)

    async def get_by_session_id(self, session_id: UUID) -> PhotoProcessingSession | None:
        """Get session by UUID.

        Args:
            session_id: Session UUID

        Returns:
            PhotoProcessingSession if found, None otherwise
        """
        stmt = select(self.model).where(self.model.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_storage_location(
        self, storage_location_id: int, limit: int = 50
    ) -> list[PhotoProcessingSession]:
        """Get sessions for a storage location.

        Args:
            storage_location_id: Storage location ID
            limit: Max results (default 50)

        Returns:
            List of PhotoProcessingSession ordered by created_at DESC
        """
        stmt = (
            select(self.model)
            .where(self.model.storage_location_id == storage_location_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: ProcessingSessionStatusEnum, limit: int = 100
    ) -> list[PhotoProcessingSession]:
        """Get sessions by status.

        Args:
            status: Processing status
            limit: Max results (default 100)

        Returns:
            List of PhotoProcessingSession ordered by created_at DESC
        """
        stmt = (
            select(self.model)
            .where(self.model.status == status)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> list[PhotoProcessingSession]:
        """Get sessions within date range.

        Args:
            start_date: Start datetime (inclusive)
            end_date: End datetime (inclusive)
            limit: Max results (default 100)

        Returns:
            List of PhotoProcessingSession ordered by created_at DESC
        """
        stmt = (
            select(self.model)
            .where(
                self.model.created_at >= start_date,
                self.model.created_at <= end_date,
            )
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
