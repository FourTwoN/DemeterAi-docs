"""Storage bin type business logic service (simple CRUD lookup table)."""

from app.repositories.storage_bin_type_repository import StorageBinTypeRepository
from app.schemas.storage_bin_type_schema import StorageBinTypeCreateRequest, StorageBinTypeResponse


class StorageBinTypeService:
    """Simple CRUD operations for bin types (lookup table)."""

    def __init__(self, bin_type_repo: StorageBinTypeRepository) -> None:
        self.bin_type_repo = bin_type_repo

    async def create_bin_type(self, request: StorageBinTypeCreateRequest) -> StorageBinTypeResponse:
        type_data = request.model_dump()
        type_model = await self.bin_type_repo.create(type_data)
        return StorageBinTypeResponse.from_model(type_model)

    async def get_bin_type_by_id(self, type_id: int) -> StorageBinTypeResponse:
        type_model = await self.bin_type_repo.get(type_id)
        if not type_model:
            raise ValueError(f"BinType {type_id} not found")
        return StorageBinTypeResponse.from_model(type_model)

    async def get_all_bin_types(self) -> list[StorageBinTypeResponse]:
        types = await self.bin_type_repo.get_multi(limit=100)
        return [StorageBinTypeResponse.from_model(t) for t in types]
