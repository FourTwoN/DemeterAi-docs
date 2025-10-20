"""Product sample image repository for product reference image data access.

Provides CRUD operations for product sample image entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_sample_image import ProductSampleImage
from app.repositories.base import AsyncRepository


class ProductSampleImageRepository(AsyncRepository[ProductSampleImage]):
    """Repository for product sample image database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(ProductSampleImage, session)
