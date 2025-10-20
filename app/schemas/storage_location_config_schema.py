"""Storage Location Config Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.storage_location_config import StorageLocationConfig


class StorageLocationConfigCreateRequest(BaseModel):
    """Request schema for creating storage location config."""

    storage_location_id: int
    product_id: int
    packaging_catalog_id: int
    product_state_id: int
    expected_quantity: int = Field(..., ge=0)


class StorageLocationConfigUpdateRequest(BaseModel):
    """Request schema for updating storage location config."""

    product_id: int | None = None
    packaging_catalog_id: int | None = None
    product_state_id: int | None = None
    expected_quantity: int | None = Field(None, ge=0)


class StorageLocationConfigResponse(BaseModel):
    """Response schema for storage location config."""

    storage_location_config_id: int
    storage_location_id: int
    product_id: int
    packaging_catalog_id: int
    product_state_id: int
    expected_quantity: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "StorageLocationConfig") -> "StorageLocationConfigResponse":
        return cls(
            storage_location_config_id=model.storage_location_config_id,
            storage_location_id=model.storage_location_id,
            product_id=model.product_id,
            packaging_catalog_id=model.packaging_catalog_id,
            product_state_id=model.product_state_id,
            expected_quantity=model.expected_quantity,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
