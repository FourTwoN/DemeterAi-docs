"""DensityParameter business logic service."""

from app.repositories.density_parameter_repository import DensityParameterRepository
from app.schemas.density_parameter_schema import (
    DensityParameterCreateRequest,
    DensityParameterResponse,
    DensityParameterUpdateRequest,
)


class DensityParameterService:
    """Business logic for densityparameter operations (CRUD)."""

    def __init__(self, repo: DensityParameterRepository) -> None:
        self.repo = repo

    async def create(self, request: DensityParameterCreateRequest) -> DensityParameterResponse:
        """Create a new densityparameter."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return DensityParameterResponse.from_model(model)

    async def get_by_id(self, id: int) -> DensityParameterResponse:
        """Get densityparameter by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("DensityParameter {id} not found")
        return DensityParameterResponse.from_model(model)

    async def get_all(self, limit: int = 100) -> list[DensityParameterResponse]:
        """Get all densityparameters."""
        models = await self.repo.get_multi(limit=limit)
        return [DensityParameterResponse.from_model(m) for m in models]

    async def update(
        self, id: int, request: DensityParameterUpdateRequest
    ) -> DensityParameterResponse:
        """Update densityparameter."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("DensityParameter {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return DensityParameterResponse.from_model(updated_model)

    async def delete(self, id: int) -> None:
        """Delete densityparameter."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("DensityParameter {id} not found")
        await self.repo.delete(id)
