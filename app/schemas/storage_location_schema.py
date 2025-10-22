"""Storage Location Pydantic schemas for request/response validation.

Schemas for StorageLocationService layer (Level 3 of location hierarchy).
Critical for photo localization and ML pipeline processing.

Key Features:
- Point geometry for GPS coordinates (single photo location)
- QR code validation for physical tracking
- position_metadata JSONB for flexible camera/lighting data
- Integration with StorageLocationConfig (expected products)

Architecture:
    Layer: Application (Schemas)
    Dependencies: Pydantic 2.5+, GeoAlchemy2, app.models.storage_location
    Used by: StorageLocationService, StorageLocationController

See:
    - Task: backlog/03_kanban/00_backlog/S003-storage-location-service.md
    - Model: app/models/storage_location.py
    - Service: app/services/storage_location_service.py
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StorageLocationCreateRequest(BaseModel):
    """Request schema for creating a new storage location."""

    storage_area_id: int = Field(..., description="Parent storage area ID", gt=0)
    code: str = Field(..., min_length=2, max_length=50, description="Unique location code")
    name: str = Field(..., min_length=1, max_length=200, description="Location name")
    qr_code: str | None = Field(None, min_length=8, max_length=20, description="QR code")
    coordinates: dict[str, Any] = Field(..., description="GPS point (GeoJSON format)")
    position_metadata: dict[str, Any] | None = Field(None, description="Camera/lighting metadata")
    active: bool = Field(default=True, description="Active status")

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        if not v.isupper():
            raise ValueError(f"Location code must be uppercase (got: {v})")
        import re

        if not re.match(r"^[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+$", v):
            raise ValueError(f"Location code must match WAREHOUSE-AREA-LOCATION pattern (got: {v})")
        return v

    @field_validator("coordinates")
    @classmethod
    def validate_geojson_point(cls, v: dict[str, Any]) -> dict[str, Any]:
        if v.get("type") != "Point":
            raise ValueError(f"Expected GeoJSON type 'Point', got '{v.get('type')}'")
        if "coordinates" not in v or len(v["coordinates"]) != 2:
            raise ValueError("Point coordinates must have [longitude, latitude]")
        return v


class StorageLocationUpdateRequest(BaseModel):
    """Request schema for updating an existing storage location."""

    code: str | None = Field(None, min_length=2, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=200)
    qr_code: str | None = Field(None, min_length=8, max_length=20)
    coordinates: dict[str, Any] | None = None
    position_metadata: dict[str, Any] | None = None
    active: bool | None = None


class StorageLocationResponse(BaseModel):
    """Response schema for storage location data."""

    storage_location_id: int
    storage_area_id: int
    code: str
    name: str
    qr_code: str | None
    coordinates: dict[str, Any]  # GeoJSON Point
    centroid: dict[str, Any] | None  # GeoJSON Point (same as coordinates)
    area_m2: float | None  # Always 0 for POINT
    position_metadata: dict[str, Any] | None
    active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, location: Any) -> "StorageLocationResponse":
        """Transform SQLAlchemy StorageLocation to Pydantic schema."""
        from geoalchemy2.shape import to_shape

        # Convert PostGIS POINT to GeoJSON
        coords_geojson = to_shape(location.coordinates).__geo_interface__
        centroid = to_shape(location.centroid).__geo_interface__ if location.centroid else None

        return cls(
            storage_location_id=location.storage_location_id,
            storage_area_id=location.storage_area_id,
            code=location.code,
            name=location.name,
            qr_code=location.qr_code,
            coordinates=coords_geojson,
            centroid=centroid,
            area_m2=float(location.area_m2) if location.area_m2 else 0.0,
            position_metadata=location.position_metadata,
            active=location.active,
            created_at=location.created_at,
            updated_at=location.updated_at,
        )
