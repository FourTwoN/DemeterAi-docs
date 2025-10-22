"""PackagingType business logic service."""

from app.repositories.packaging_type_repository import PackagingTypeRepository
from app.schemas.packaging_type_schema import (
    PackagingTypeCreateRequest,
    PackagingTypeResponse,
    PackagingTypeUpdateRequest,
)


class PackagingTypeService:
    """Business logic for packagingtype operations (CRUD)."""

    def __init__(self, repo: PackagingTypeRepository) -> None:
        self.repo = repo

    async def create(self, request: PackagingTypeCreateRequest) -> PackagingTypeResponse:
        """Create a new packagingtype."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return PackagingTypeResponse.model_validate(model)

    async def get_by_id(self, id: int) -> PackagingTypeResponse:
        """Get packagingtype by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingType {id} not found")
        return PackagingTypeResponse.model_validate(model)

    async def get_all(self, limit: int = 100) -> list[PackagingTypeResponse]:
        """Get all packagingtypes."""
        models = await self.repo.get_multi(limit=limit)
        return [PackagingTypeResponse.model_validate(m) for m in models]

    async def update(self, id: int, request: PackagingTypeUpdateRequest) -> PackagingTypeResponse:
        """Update packagingtype."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingType {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return PackagingTypeResponse.model_validate(updated_model)

    async def delete(self, id: int) -> None:
        """Delete packagingtype."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingType {id} not found")
        await self.repo.delete(id)
