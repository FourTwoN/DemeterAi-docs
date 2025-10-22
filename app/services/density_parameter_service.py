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
        return DensityParameterResponse.model_validate(model)

    async def get_by_id(self, id: int) -> DensityParameterResponse:
        """Get densityparameter by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("DensityParameter {id} not found")
        return DensityParameterResponse.model_validate(model)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[DensityParameterResponse]:
        """Get all densityparameters."""
        models = await self.repo.get_multi(skip=skip, limit=limit)
        return [DensityParameterResponse.model_validate(m) for m in models]

    async def update(
        self, id: int, request: DensityParameterUpdateRequest
    ) -> DensityParameterResponse:
        """Update densityparameter."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("DensityParameter {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        return DensityParameterResponse.model_validate(updated_model)

    async def delete(self, id: int) -> None:
        """Delete densityparameter."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("DensityParameter {id} not found")
        await self.repo.delete(id)

    async def get_by_product_and_packaging(
        self, product_id: int, packaging_catalog_id: int
    ) -> DensityParameterResponse | None:
        """Get density parameter for product and packaging combination."""
        from sqlalchemy import select

        from app.models.density_parameter import DensityParameter

        stmt = select(DensityParameter).where(
            (DensityParameter.product_id == product_id)
            & (DensityParameter.packaging_catalog_id == packaging_catalog_id)
        )
        result = await self.repo.session.execute(stmt)
        model = result.scalars().first()
        return DensityParameterResponse.model_validate(model) if model else None

    async def get_by_product(self, product_id: int) -> list[DensityParameterResponse]:
        """Get all density parameters for a product."""
        from sqlalchemy import select

        from app.models.density_parameter import DensityParameter

        stmt = select(DensityParameter).where(DensityParameter.product_id == product_id)
        result = await self.repo.session.execute(stmt)
        models = result.scalars().all()
        return [DensityParameterResponse.model_validate(m) for m in models]
