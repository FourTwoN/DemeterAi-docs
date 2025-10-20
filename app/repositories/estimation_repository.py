"""Estimation repository for plant count estimation data access.

Provides CRUD operations for estimation entities from ML pipeline.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimation import Estimation
from app.repositories.base import AsyncRepository


class EstimationRepository(AsyncRepository[Estimation]):
    """Repository for estimation database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Estimation, session)
