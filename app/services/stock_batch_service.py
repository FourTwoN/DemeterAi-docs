"""Stock batch business logic service (inventory tracking)."""

from app.repositories.stock_batch_repository import StockBatchRepository
from app.schemas.stock_batch_schema import StockBatchCreateRequest, StockBatchResponse


class StockBatchService:
    """Service for stock batch inventory operations."""

    def __init__(self, batch_repo: StockBatchRepository) -> None:
        self.batch_repo = batch_repo

    async def create_stock_batch(self, request: StockBatchCreateRequest) -> StockBatchResponse:
        """Create new stock batch."""
        # Check code uniqueness
        existing = await self.batch_repo.get_by_field("batch_code", request.batch_code)
        if existing:
            raise ValueError(f"Batch code '{request.batch_code}' already exists")

        batch_data = request.model_dump()
        batch = await self.batch_repo.create(batch_data)
        return StockBatchResponse.model_validate(batch)

    async def get_batch_by_id(self, batch_id: int) -> StockBatchResponse:
        """Get stock batch by ID."""
        batch = await self.batch_repo.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        return StockBatchResponse.model_validate(batch)

    async def update_batch_quantity(self, batch_id: int, new_quantity: int) -> StockBatchResponse:
        """Update current quantity for a batch."""
        updated = await self.batch_repo.update(batch_id, {"quantity_current": new_quantity})
        return StockBatchResponse.model_validate(updated)
