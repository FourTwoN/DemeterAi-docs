"""Classification repository for ML classification data access.

Provides CRUD operations for classification entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classification import Classification
from app.repositories.base import AsyncRepository


class ClassificationRepository(AsyncRepository[Classification]):
    """Repository for classification database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Classification, session)
