"""PackagingMaterial business logic service."""

from app.repositories.packaging_material_repository import PackagingMaterialRepository
from app.schemas.packaging_material_schema import (
    PackagingMaterialCreateRequest,
    PackagingMaterialResponse,
    PackagingMaterialUpdateRequest,
)


class PackagingMaterialService:
    """Business logic for packagingmaterial operations (CRUD)."""

    def __init__(self, repo: PackagingMaterialRepository) -> None:
        self.repo = repo

    async def create(self, request: PackagingMaterialCreateRequest) -> PackagingMaterialResponse:
        """Create a new packagingmaterial."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return PackagingMaterialResponse.model_validate(model)

    async def get_by_id(self, id: int) -> PackagingMaterialResponse:
        """Get packagingmaterial by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingMaterial {id} not found")
        return PackagingMaterialResponse.model_validate(model)

    async def get_all(self, limit: int = 100) -> list[PackagingMaterialResponse]:
        """Get all packagingmaterials."""
        models = await self.repo.get_multi(limit=limit)
        return [PackagingMaterialResponse.model_validate(m) for m in models]

    async def update(
        self, id: int, request: PackagingMaterialUpdateRequest
    ) -> PackagingMaterialResponse:
        """Update packagingmaterial."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingMaterial {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return PackagingMaterialResponse.model_validate(updated_model)

    async def delete(self, id: int) -> None:
        """Delete packagingmaterial."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingMaterial {id} not found")
        await self.repo.delete(id)
