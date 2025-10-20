"""S3 image repository for cloud image metadata data access.

Provides CRUD operations for S3 image entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.s3_image import S3Image
from app.repositories.base import AsyncRepository


class S3ImageRepository(AsyncRepository[S3Image]):
    """Repository for S3 image database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(S3Image, session)
