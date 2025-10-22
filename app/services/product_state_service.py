"""ProductState business logic service."""

from app.repositories.product_state_repository import ProductStateRepository
from app.schemas.product_state_schema import (
    ProductStateCreateRequest,
    ProductStateResponse,
    ProductStateUpdateRequest,
)


class ProductStateService:
    """Business logic for productstate operations (CRUD)."""

    def __init__(self, repo: ProductStateRepository) -> None:
        self.repo = repo

    async def create(self, request: ProductStateCreateRequest) -> ProductStateResponse:
        """Create a new productstate."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return ProductStateResponse.from_model(model)

    async def get_by_id(self, id: int) -> ProductStateResponse:
        """Get productstate by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("ProductState {id} not found")
        return ProductStateResponse.from_model(model)

    async def get_all(self, limit: int = 100) -> list[ProductStateResponse]:
        """Get all productstates."""
        models = await self.repo.get_multi(limit=limit)
        return [ProductStateResponse.from_model(m) for m in models]

    async def update(self, id: int, request: ProductStateUpdateRequest) -> ProductStateResponse:
        """Update productstate."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("ProductState {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        if updated_model is None:
            raise ValueError(f"Failed to update ProductState {id}")
        return ProductStateResponse.from_model(updated_model)

    async def delete(self, id: int) -> None:
        """Delete productstate."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("ProductState {id} not found")
        await self.repo.delete(id)
