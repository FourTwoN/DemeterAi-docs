"""Storage Bin Type Pydantic schemas (simple lookup table)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StorageBinTypeCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class StorageBinTypeResponse(BaseModel):
    storage_bin_type_id: int
    code: str
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, type_model: Any) -> "StorageBinTypeResponse":
        """Create response from SQLAlchemy model."""
        return cls(
            storage_bin_type_id=type_model.storage_bin_type_id,
            code=type_model.code,
            name=type_model.name,
            description=type_model.description,
            created_at=type_model.created_at,
        )
