"""Stock Movement Pydantic schemas (audit trail)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StockMovementCreateRequest(BaseModel):
    batch_id: int = Field(..., gt=0)
    movement_type: str
    quantity: int
    user_id: int = Field(..., gt=0)
    source_type: str = Field(default="manual")
    is_inbound: bool
    reason_description: str | None = None
    source_bin_id: int | None = None
    destination_bin_id: int | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    processing_session_id: int | None = None


class StockMovementResponse(BaseModel):
    id: int
    movement_id: UUID
    batch_id: int
    movement_type: str
    quantity: int
    user_id: int
    source_type: str
    is_inbound: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
