"""Storage Bin Pydantic schemas (Level 4 - leaf level)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StorageBinCreateRequest(BaseModel):
    storage_location_id: int = Field(..., gt=0)
    storage_bin_type_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=2, max_length=100)
    label: str = Field(..., min_length=1, max_length=200)
    position_metadata: dict[str, Any] | None = None
    status: str = Field(default="active")


class StorageBinResponse(BaseModel):
    storage_bin_id: int
    storage_location_id: int
    storage_bin_type_id: int
    code: str
    label: str
    position_metadata: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, bin_model):
        return cls(
            storage_bin_id=bin_model.storage_bin_id,
            storage_location_id=bin_model.storage_location_id,
            storage_bin_type_id=bin_model.storage_bin_type_id,
            code=bin_model.code,
            label=bin_model.label,
            position_metadata=bin_model.position_metadata,
            status=bin_model.status.value
            if hasattr(bin_model.status, "value")
            else bin_model.status,
            created_at=bin_model.created_at,
            updated_at=bin_model.updated_at,
        )
