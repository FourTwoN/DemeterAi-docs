"""Stock movement business logic service (audit trail)."""

import uuid

from app.repositories.stock_movement_repository import StockMovementRepository
from app.schemas.stock_movement_schema import StockMovementCreateRequest, StockMovementResponse


class StockMovementService:
    """Service for stock movement audit trail operations."""

    def __init__(self, movement_repo: StockMovementRepository) -> None:
        self.movement_repo = movement_repo

    async def create_stock_movement(
        self, request: StockMovementCreateRequest
    ) -> StockMovementResponse:
        """Create stock movement with UUID for idempotency."""
        movement_data = request.model_dump()
        movement_data["movement_id"] = uuid.uuid4()

        movement = await self.movement_repo.create(movement_data)
        return StockMovementResponse.model_validate(movement)

    async def get_movements_by_batch(self, batch_id: int) -> list[StockMovementResponse]:
        """Get all movements for a stock batch."""
        from sqlalchemy import select

        query = (
            select(self.movement_repo.model)
            .where(self.movement_repo.model.batch_id == batch_id)
            .order_by(self.movement_repo.model.created_at.desc())
        )

        result = await self.movement_repo.session.execute(query)
        movements = result.scalars().all()
        return [StockMovementResponse.model_validate(m) for m in movements]
