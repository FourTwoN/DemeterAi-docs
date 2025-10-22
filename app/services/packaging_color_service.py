"""PackagingColor business logic service."""

from app.repositories.packaging_color_repository import PackagingColorRepository
from app.schemas.packaging_color_schema import (
    PackagingColorCreateRequest,
    PackagingColorResponse,
    PackagingColorUpdateRequest,
)


class PackagingColorService:
    """Business logic for packagingcolor operations (CRUD)."""

    def __init__(self, repo: PackagingColorRepository) -> None:
        self.repo = repo

    async def create(self, request: PackagingColorCreateRequest) -> PackagingColorResponse:
        """Create a new packagingcolor."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return PackagingColorResponse.model_validate(model)

    async def get_by_id(self, id: int) -> PackagingColorResponse:
        """Get packagingcolor by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingColor {id} not found")
        return PackagingColorResponse.model_validate(model)

    async def get_all(self, limit: int = 100) -> list[PackagingColorResponse]:
        """Get all packagingcolors."""
        models = await self.repo.get_multi(limit=limit)
        return [PackagingColorResponse.model_validate(m) for m in models]

    async def update(self, id: int, request: PackagingColorUpdateRequest) -> PackagingColorResponse:
        """Update packagingcolor."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingColor {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return PackagingColorResponse.model_validate(updated_model)

    async def delete(self, id: int) -> None:
        """Delete packagingcolor."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("PackagingColor {id} not found")
        await self.repo.delete(id)
