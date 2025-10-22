"""Storage Location Config Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.storage_location_config import StorageLocationConfig


class StorageLocationConfigCreateRequest(BaseModel):
    """Request schema for creating storage location config."""

    storage_location_id: int
    product_id: int
    packaging_catalog_id: int | None = None
    expected_product_state_id: int
    area_cm2: float = Field(..., gt=0)
    notes: str | None = None


class StorageLocationConfigUpdateRequest(BaseModel):
    """Request schema for updating storage location config."""

    product_id: int | None = None
    packaging_catalog_id: int | None = None
    expected_product_state_id: int | None = None
    area_cm2: float | None = Field(None, gt=0)
    notes: str | None = None


class StorageLocationConfigResponse(BaseModel):
    """Response schema for storage location config."""

    id: int
    storage_location_id: int
    product_id: int
    packaging_catalog_id: int | None
    expected_product_state_id: int
    area_cm2: float
    active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "StorageLocationConfig") -> "StorageLocationConfigResponse":
        from decimal import Decimal

        return cls(
            id=cast(int, model.id),
            storage_location_id=cast(int, model.storage_location_id),
            product_id=cast(int, model.product_id),
            packaging_catalog_id=model.packaging_catalog_id,
            expected_product_state_id=cast(int, model.expected_product_state_id),
            area_cm2=cast(
                float,
                float(model.area_cm2) if isinstance(model.area_cm2, Decimal) else model.area_cm2,
            ),
            active=cast(bool, model.active),
            notes=model.notes,
            created_at=cast(datetime, model.created_at),
            updated_at=model.updated_at,
        )
