"""Storage Area Pydantic schemas for request/response validation.

This module provides Pydantic schemas for StorageAreaService layer,
handling validation, serialization, and PostGIS geometry transformations.

Key Features:
- GeoJSON format for geometry (standard for web APIs)
- PostGIS geometry ↔ GeoJSON conversion
- Parent warehouse validation
- Partial updates with exclude_unset
- Type validation with Pydantic v2

Architecture:
    Layer: Application (Schemas)
    Dependencies: Pydantic 2.5+, GeoAlchemy2, app.models.storage_area
    Used by: StorageAreaService, StorageAreaController

Example:
    ```python
    # Request validation
    request = StorageAreaCreateRequest(
        warehouse_id=1,
        code="INV01-NORTH",
        name="North Wing",
        position="N",
        geojson_coordinates={
            "type": "Polygon",
            "coordinates": [[...]]
        }
    )

    # Response serialization
    response = StorageAreaResponse.from_model(storage_area_model)
    ```

See:
    - Task: backlog/03_kanban/00_backlog/S002-storage-area-service.md
    - Model: app/models/storage_area.py
    - Service: app/services/storage_area_service.py
"""

from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.storage_area import PositionEnum, StorageArea


class StorageAreaCreateRequest(BaseModel):
    """Request schema for creating a new storage area.

    Attributes:
        warehouse_id: Parent warehouse ID (foreign key)
        parent_area_id: Optional parent area for hierarchical subdivision
        code: Unique area code (format: WAREHOUSE-AREA, uppercase)
        name: Human-readable area name
        position: Cardinal direction (N/S/E/W/C, optional)
        geojson_coordinates: Area boundary as GeoJSON Polygon
        active: Active status (default: True)

    Example:
        ```python
        request = StorageAreaCreateRequest(
            warehouse_id=1,
            code="INV01-NORTH",
            name="North Wing",
            position="N",
            geojson_coordinates={
                "type": "Polygon",
                "coordinates": [[
                    [-70.648, -33.449], [-70.647, -33.449],
                    [-70.647, -33.450], [-70.648, -33.450],
                    [-70.648, -33.449]
                ]]
            }
        )
        ```
    """

    warehouse_id: int = Field(..., description="Parent warehouse ID", gt=0)
    parent_area_id: int | None = Field(
        None, description="Parent area ID for hierarchical subdivision", gt=0
    )
    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Unique area code (format: WAREHOUSE-AREA, uppercase)",
    )
    name: str = Field(..., min_length=1, max_length=200, description="Area name")
    position: PositionEnum | None = Field(None, description="Cardinal direction (N/S/E/W/C)")
    geojson_coordinates: dict[str, Any] = Field(
        ..., description="Area boundary polygon (GeoJSON format)"
    )
    active: bool = Field(default=True, description="Active status (soft delete flag)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "warehouse_id": 1,
                "parent_area_id": None,
                "code": "INV01-NORTH",
                "name": "North Wing",
                "position": "N",
                "geojson_coordinates": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-70.648300, -33.448900],
                            [-70.647300, -33.448900],
                            [-70.647300, -33.449900],
                            [-70.648300, -33.449900],
                            [-70.648300, -33.448900],
                        ]
                    ],
                },
                "active": True,
            }
        }
    )

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        """Validate area code format.

        Rules:
            - Must be uppercase
            - Format: WAREHOUSE-AREA (e.g., INV01-NORTH)

        Args:
            v: Area code to validate

        Returns:
            Validated code (uppercase)

        Raises:
            ValueError: If code format is invalid
        """
        if not v.isupper():
            raise ValueError(f"Storage area code must be uppercase (got: {v})")

        import re

        if not re.match(r"^[A-Z0-9_-]+-[A-Z0-9_-]+$", v):
            raise ValueError(f"Storage area code must match pattern WAREHOUSE-AREA (got: {v})")

        return v

    @field_validator("geojson_coordinates")
    @classmethod
    def validate_geojson_type(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate GeoJSON has correct type.

        Args:
            v: GeoJSON dictionary

        Returns:
            Validated GeoJSON

        Raises:
            ValueError: If type is not Polygon
        """
        if v.get("type") != "Polygon":
            raise ValueError(f"Expected GeoJSON type 'Polygon', got '{v.get('type')}'")

        if "coordinates" not in v:
            raise ValueError("GeoJSON must have 'coordinates' field")

        return v


class StorageAreaUpdateRequest(BaseModel):
    """Request schema for updating an existing storage area.

    All fields are optional (partial update supported).

    Attributes:
        code: New area code (optional)
        name: New area name (optional)
        position: New cardinal direction (optional)
        geojson_coordinates: New boundary polygon (optional)
        parent_area_id: New parent area (optional)
        active: New active status (optional)

    Example:
        ```python
        # Partial update (only name)
        request = StorageAreaUpdateRequest(name="Updated North Wing")

        # Multiple fields
        request = StorageAreaUpdateRequest(
            name="Updated Name",
            active=False
        )
        ```
    """

    code: str | None = Field(None, min_length=2, max_length=50, description="Area code")
    name: str | None = Field(None, min_length=1, max_length=200, description="Area name")
    position: PositionEnum | None = Field(None, description="Cardinal direction")
    geojson_coordinates: dict[str, Any] | None = Field(
        None, description="Area boundary polygon (GeoJSON format)"
    )
    parent_area_id: int | None = Field(None, description="Parent area ID", gt=0)
    active: bool | None = Field(None, description="Active status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated North Wing",
                "active": True,
            }
        }
    )

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str | None) -> str | None:
        """Validate area code format if provided."""
        if v is None:
            return v

        if not v.isupper():
            raise ValueError(f"Storage area code must be uppercase (got: {v})")

        import re

        if not re.match(r"^[A-Z0-9_-]+-[A-Z0-9_-]+$", v):
            raise ValueError(f"Storage area code must match pattern WAREHOUSE-AREA (got: {v})")

        return v

    @field_validator("geojson_coordinates")
    @classmethod
    def validate_geojson_type(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate GeoJSON type if provided."""
        if v is None:
            return v

        if v.get("type") != "Polygon":
            raise ValueError(f"Expected GeoJSON type 'Polygon', got '{v.get('type')}'")

        if "coordinates" not in v:
            raise ValueError("GeoJSON must have 'coordinates' field")

        return v


class StorageAreaResponse(BaseModel):
    """Response schema for storage area data.

    Transforms SQLAlchemy StorageArea model to JSON-serializable format.
    PostGIS geometry is converted to GeoJSON standard format.

    Attributes:
        storage_area_id: Primary key
        warehouse_id: Parent warehouse ID
        parent_area_id: Parent area ID (nullable)
        code: Unique area code
        name: Area name
        position: Cardinal direction (nullable)
        geojson_coordinates: Boundary polygon (GeoJSON format)
        centroid: Center point (GeoJSON format, nullable)
        area_m2: Calculated area in square meters (nullable)
        active: Active status
        created_at: Creation timestamp
        updated_at: Last update timestamp (nullable)

    Example:
        ```python
        # Transform from SQLAlchemy model
        response = StorageAreaResponse.from_model(storage_area)

        # JSON serialization (for FastAPI response)
        return response  # FastAPI auto-converts to JSON
        ```
    """

    storage_area_id: int = Field(..., description="Primary key")
    warehouse_id: int = Field(..., description="Parent warehouse ID")
    parent_area_id: int | None = Field(None, description="Parent area ID")
    code: str = Field(..., description="Unique area code")
    name: str = Field(..., description="Area name")
    position: str | None = Field(None, description="Cardinal direction (N/S/E/W/C)")
    geojson_coordinates: dict[str, Any] = Field(..., description="Area boundary (GeoJSON Polygon)")
    centroid: dict[str, Any] | None = Field(None, description="Center point (GeoJSON Point)")
    area_m2: float | None = Field(None, description="Calculated area in square meters")
    active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "storage_area_id": 1,
                "warehouse_id": 1,
                "parent_area_id": None,
                "code": "INV01-NORTH",
                "name": "North Wing",
                "position": "N",
                "geojson_coordinates": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-70.648300, -33.448900],
                            [-70.647300, -33.448900],
                            [-70.647300, -33.449900],
                            [-70.648300, -33.449900],
                            [-70.648300, -33.448900],
                        ]
                    ],
                },
                "centroid": {"type": "Point", "coordinates": [-70.6478, -33.4494]},
                "area_m2": 5250.25,
                "active": True,
                "created_at": "2025-10-20T14:30:00Z",
                "updated_at": None,
            }
        },
    )

    @classmethod
    def from_model(cls, area: StorageArea) -> "StorageAreaResponse":
        """Transform SQLAlchemy StorageArea model to Pydantic schema.

        Converts PostGIS geometry columns to GeoJSON format using GeoAlchemy2.

        Args:
            area: SQLAlchemy StorageArea instance

        Returns:
            StorageAreaResponse with GeoJSON geometry

        Example:
            ```python
            area = await repo.get(123)
            response = StorageAreaResponse.from_model(area)
            ```
        """
        from geoalchemy2.shape import to_shape

        # Convert PostGIS geometry to GeoJSON
        geojson = to_shape(area.geojson_coordinates).__geo_interface__

        # Convert centroid if present (nullable)
        centroid = None
        if area.centroid is not None:
            centroid = to_shape(area.centroid).__geo_interface__

        return cls(
            storage_area_id=cast(int, area.storage_area_id),
            warehouse_id=cast(int, area.warehouse_id),
            parent_area_id=area.parent_area_id,
            code=cast(str, area.code),
            name=cast(str, area.name),
            position=area.position.value if area.position else None,
            geojson_coordinates=geojson,
            centroid=centroid,
            area_m2=float(area.area_m2) if area.area_m2 else None,
            active=cast(bool, area.active),
            created_at=cast(datetime, area.created_at),
            updated_at=area.updated_at,
        )


class StorageLocationSummary(BaseModel):
    """Summary schema for storage locations (used in StorageAreaWithLocationsResponse).

    Attributes:
        storage_location_id: Primary key
        code: Unique location code
        name: Location name
        active: Active status
    """

    storage_location_id: int = Field(..., description="Primary key")
    code: str = Field(..., description="Unique location code")
    name: str = Field(..., description="Location name")
    active: bool = Field(..., description="Active status")

    model_config = ConfigDict(from_attributes=True)


class StorageAreaWithLocationsResponse(StorageAreaResponse):
    """Extended storage area response including storage locations.

    Inherits all fields from StorageAreaResponse and adds storage_locations list.

    Attributes:
        storage_locations: List of storage locations within this area

    Example:
        ```python
        # Get area with locations
        areas = await service.get_areas_by_warehouse(1, include_locations=True)
        # areas[0].storage_locations -> list of locations
        ```
    """

    storage_locations: list[StorageLocationSummary] = Field(
        default_factory=list, description="Storage locations within this area"
    )

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, area: StorageArea) -> "StorageAreaWithLocationsResponse":
        """Transform StorageArea model with storage_locations relationship.

        Args:
            area: StorageArea instance with storage_locations loaded

        Returns:
            StorageAreaWithLocationsResponse with locations list
        """
        # Use parent class method for base fields
        base_response = StorageAreaResponse.from_model(area)

        # Add storage locations if present
        storage_locations = []
        if hasattr(area, "storage_locations") and area.storage_locations:
            storage_locations = [
                StorageLocationSummary.model_validate(loc) for loc in area.storage_locations
            ]

        return cls(**base_response.model_dump(), storage_locations=storage_locations)
