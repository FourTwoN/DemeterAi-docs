"""Density parameter repository for calibration parameter data access.

Provides CRUD operations for density parameter entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.density_parameter import DensityParameter
from app.repositories.base import AsyncRepository


class DensityParameterRepository(AsyncRepository[DensityParameter]):
    """Repository for density parameter database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(DensityParameter, session)
