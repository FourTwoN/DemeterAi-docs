"""StorageLocationConfig business logic service."""

from app.repositories.storage_location_config_repository import StorageLocationConfigRepository
from app.schemas.storage_location_config_schema import (
    StorageLocationConfigCreateRequest,
    StorageLocationConfigResponse,
    StorageLocationConfigUpdateRequest,
)


class StorageLocationConfigService:
    """Business logic for storagelocationconfig operations (CRUD)."""

    def __init__(self, repo: StorageLocationConfigRepository) -> None:
        self.repo = repo

    async def create(
        self, request: StorageLocationConfigCreateRequest
    ) -> StorageLocationConfigResponse:
        """Create a new storagelocationconfig."""
        data = request.model_dump()
        model = await self.repo.create(data)
        return StorageLocationConfigResponse.from_model(model)

    async def get_by_id(self, id: int) -> StorageLocationConfigResponse:
        """Get storagelocationconfig by ID."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("StorageLocationConfig {id} not found")
        return StorageLocationConfigResponse.from_model(model)

    async def get_all(self, limit: int = 100) -> list[StorageLocationConfigResponse]:
        """Get all storagelocationconfigs."""
        models = await self.repo.get_multi(limit=limit)
        return [StorageLocationConfigResponse.from_model(m) for m in models]

    async def update(
        self, id: int, request: StorageLocationConfigUpdateRequest
    ) -> StorageLocationConfigResponse:
        """Update storagelocationconfig."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("StorageLocationConfig {id} not found")

        update_data = request.model_dump(exclude_unset=True)
        updated_model = await self.repo.update(id, update_data)
        if not updated_model:
            raise ValueError(f"StorageLocationConfig {id} not found after update")
        return StorageLocationConfigResponse.from_model(updated_model)

    async def delete(self, id: int) -> None:
        """Delete storagelocationconfig."""
        model = await self.repo.get(id)
        if not model:
            raise ValueError("StorageLocationConfig {id} not found")
        await self.repo.delete(id)

    async def get_by_location(self, location_id: int) -> StorageLocationConfigResponse | None:
        """Get configuration for a specific location."""
        # Query by storage_location_id
        from sqlalchemy import select

        from app.models.storage_location_config import StorageLocationConfig

        stmt = select(StorageLocationConfig).where(
            StorageLocationConfig.storage_location_id == location_id
        )
        result = await self.repo.session.execute(stmt)
        model = result.scalars().first()
        return StorageLocationConfigResponse.from_model(model) if model else None

    async def create_or_update(
        self, request: StorageLocationConfigCreateRequest
    ) -> StorageLocationConfigResponse:
        """Create or update configuration for a location."""
        # Check if config exists for this location
        existing = await self.get_by_location(request.storage_location_id)

        if existing:
            # Update existing
            update_data = request.model_dump(exclude_unset=True)
            updated_model = await self.repo.update(existing.id, update_data)
            if not updated_model:
                raise ValueError(f"StorageLocationConfig {existing.id} not found after update")
            return StorageLocationConfigResponse.from_model(updated_model)
        else:
            # Create new
            return await self.create(request)
