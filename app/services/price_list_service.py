"""PriceList business logic service."""

from app.repositories.price_list_repository import PriceListRepository
from app.schemas.price_list_schema import (
    PriceListCreateRequest,
    PriceListResponse,
    PriceListUpdateRequest,
)


class PriceListService:
    """Business logic for pricelist operations (CRUD)."""

    def __init__(self, repo: PriceListRepository) -> None:
        self.repo = repo

    async def create(self, request: PriceListCreateRequest) -> PriceListResponse:
        """Create a new pricelist."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return PriceListResponse.from_model(model)

    async def get_by_id(self, id: int) -> PriceListResponse:
        """Get pricelist by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PriceList {id} not found")
        return PriceListResponse.from_model(model)

    async def get_all(self, limit: int = 100) -> list[PriceListResponse]:
        """Get all pricelists."""
        models = await self.repo.get_multi(limit=limit)
        return [PriceListResponse.from_model(m) for m in models]

    async def update(self, id: int, request: PriceListUpdateRequest) -> PriceListResponse:
        """Update pricelist."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PriceList {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return PriceListResponse.from_model(updated_model)

    async def delete(self, id: int) -> None:
        """Delete pricelist."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PriceList {id} not found")
        await self.repo.delete(id)
