"""Estimation repository for plant count estimation data access.

Provides CRUD operations for estimation entities from ML pipeline.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimation import CalculationMethodEnum, Estimation
from app.repositories.base import AsyncRepository


class EstimationRepository(AsyncRepository[Estimation]):
    """Repository for estimation database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Estimation, session)

    async def get_by_session(self, session_id: int, limit: int = 1000) -> list[Estimation]:
        """Get all estimations for a photo processing session.

        Args:
            session_id: Photo processing session ID
            limit: Max results (default 1000)

        Returns:
            List of Estimation ordered by created_at DESC
        """
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_calculation_method(
        self, calculation_method: CalculationMethodEnum, limit: int = 100
    ) -> list[Estimation]:
        """Get estimations by calculation method.

        Args:
            calculation_method: Calculation method enum
            limit: Max results (default 100)

        Returns:
            List of Estimation ordered by created_at DESC
        """
        stmt = (
            select(self.model)
            .where(self.model.calculation_method == calculation_method)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, estimations: list[dict[str, Any]]) -> list[Estimation]:
        """Bulk create estimations (optimized for performance).

        Args:
            estimations: List of estimation dicts

        Returns:
            List of created Estimation instances

        Note:
            Uses bulk_insert for performance with large datasets.
            All estimations are flushed and refreshed to get IDs.
        """
        # Create estimation instances
        db_estimations = [Estimation(**data) for data in estimations]

        # Add all to session
        self.session.add_all(db_estimations)
        await self.session.flush()

        # Refresh all to get IDs
        for estimation in db_estimations:
            await self.session.refresh(estimation)

        return db_estimations
