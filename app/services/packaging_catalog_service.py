"""PackagingCatalog business logic service."""

from app.repositories.packaging_catalog_repository import PackagingCatalogRepository
from app.schemas.packaging_catalog_schema import (
    PackagingCatalogCreateRequest,
    PackagingCatalogResponse,
    PackagingCatalogUpdateRequest,
)


class PackagingCatalogService:
    """Business logic for packagingcatalog operations (CRUD)."""

    def __init__(self, repo: PackagingCatalogRepository) -> None:
        self.repo = repo

    async def create(self, request: PackagingCatalogCreateRequest) -> PackagingCatalogResponse:
        """Create a new packagingcatalog."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return PackagingCatalogResponse.from_model(model)

    async def get_by_id(self, id: int) -> PackagingCatalogResponse:
        """Get packagingcatalog by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingCatalog {id} not found")
        return PackagingCatalogResponse.from_model(model)

    async def get_all(self, limit: int = 100) -> list[PackagingCatalogResponse]:
        """Get all packagingcatalogs."""
        models = await self.repo.get_multi(limit=limit)
        return [PackagingCatalogResponse.from_model(m) for m in models]

    async def update(
        self, id: int, request: PackagingCatalogUpdateRequest
    ) -> PackagingCatalogResponse:
        """Update packagingcatalog."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingCatalog {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return PackagingCatalogResponse.from_model(updated_model)

    async def delete(self, id: int) -> None:
        """Delete packagingcatalog."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingCatalog {id} not found")
        await self.repo.delete(id)
