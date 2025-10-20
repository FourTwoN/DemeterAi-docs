"""Storage bin business logic service (Level 4 - leaf level)."""

from app.core.exceptions import DuplicateCodeException, StorageBinNotFoundException
from app.repositories.storage_bin_repository import StorageBinRepository
from app.schemas.storage_bin_schema import StorageBinCreateRequest, StorageBinResponse
from app.services.storage_location_service import StorageLocationService


class StorageBinService:
    """Leaf-level bin operations (no geometry, inherits from parent location)."""

    def __init__(
        self,
        bin_repo: StorageBinRepository,
        location_service: StorageLocationService,
    ) -> None:
        self.bin_repo = bin_repo
        self.location_service = location_service

    async def create_storage_bin(self, request: StorageBinCreateRequest) -> StorageBinResponse:
        # Validate parent location exists
        await self.location_service.get_storage_location_by_id(request.storage_location_id)

        # Check code uniqueness
        existing = await self.bin_repo.get_by_field("code", request.code)
        if existing:
            raise DuplicateCodeException(code=request.code)

        bin_data = request.model_dump()
        bin_model = await self.bin_repo.create(bin_data)
        return StorageBinResponse.from_model(bin_model)

    async def get_storage_bin_by_id(self, bin_id: int) -> StorageBinResponse:
        bin_model = await self.bin_repo.get(bin_id)
        if not bin_model:
            raise StorageBinNotFoundException(bin_id=bin_id)
        return StorageBinResponse.from_model(bin_model)

    async def get_bins_by_location(self, location_id: int) -> list[StorageBinResponse]:
        from sqlalchemy import select

        query = select(self.bin_repo.model).where(
            self.bin_repo.model.storage_location_id == location_id
        )
        result = await self.bin_repo.session.execute(query)
        bins = result.scalars().all()
        return [StorageBinResponse.from_model(b) for b in bins]
