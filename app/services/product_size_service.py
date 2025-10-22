"""ProductSize business logic service."""

from app.repositories.product_size_repository import ProductSizeRepository
from app.schemas.product_size_schema import (
    ProductSizeCreateRequest,
    ProductSizeResponse,
    ProductSizeUpdateRequest,
)


class ProductSizeService:
    """Business logic for productsize operations (CRUD)."""

    def __init__(self, repo: ProductSizeRepository) -> None:
        self.repo = repo

    async def create(self, request: ProductSizeCreateRequest) -> ProductSizeResponse:
        """Create a new productsize."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return ProductSizeResponse.from_model(model)

    async def get_by_id(self, id: int) -> ProductSizeResponse:
        """Get productsize by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("ProductSize {id} not found")
        return ProductSizeResponse.from_model(model)

    async def get_all(self, limit: int = 100) -> list[ProductSizeResponse]:
        """Get all productsizes."""
        models = await self.repo.get_multi(limit=limit)
        return [ProductSizeResponse.from_model(m) for m in models]

    async def update(self, id: int, request: ProductSizeUpdateRequest) -> ProductSizeResponse:
        """Update productsize."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("ProductSize {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        if updated_model is None:
            raise ValueError(f"Failed to update ProductSize {id}")
        return ProductSizeResponse.from_model(updated_model)

    async def delete(self, id: int) -> None:
        """Delete productsize."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("ProductSize {id} not found")
        await self.repo.delete(id)
