"""Warehouse Pydantic schemas for request/response validation.

This module provides Pydantic schemas for the WarehouseService layer,
handling validation, serialization, and PostGIS geometry transformations.

Key Features:
- GeoJSON format for geometry (standard for web APIs)
- PostGIS geometry ↔ GeoJSON conversion
- Partial updates with exclude_unset
- Type validation with Pydantic v2

Architecture:
    Layer: Application (Schemas)
    Dependencies: Pydantic 2.5+, GeoAlchemy2, app.models.warehouse
    Used by: WarehouseService, WarehouseController

Example:
    ```python
    # Request validation
    request = WarehouseCreateRequest(
        code="GH-001",
        name="Main Greenhouse",
        warehouse_type="greenhouse",
        geojson_coordinates={
            "type": "Polygon",
            "coordinates": [[
                [-70.648, -33.449], [-70.647, -33.449],
                [-70.647, -33.450], [-70.648, -33.450],
                [-70.648, -33.449]
            ]]
        }
    )

    # Response serialization
    response = WarehouseResponse.from_model(warehouse_model)
    ```

See:
    - Task: backlog/03_kanban/01_ready/S001-warehouse-service.md
    - Model: app/models/warehouse.py
    - Service: app/services/warehouse_service.py
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.warehouse import Warehouse, WarehouseTypeEnum


class WarehouseCreateRequest(BaseModel):
    """Request schema for creating a new warehouse.

    Attributes:
        code: Unique warehouse code (uppercase alphanumeric, 2-20 chars)
        name: Human-readable warehouse name
        warehouse_type: Facility type (greenhouse, shadehouse, open_field, tunnel)
        geojson_coordinates: Warehouse boundary as GeoJSON Polygon
        active: Active status (default: True)

    Example:
        ```python
        request = WarehouseCreateRequest(
            code="GH-001",
            name="Main Greenhouse",
            warehouse_type="greenhouse",
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

    code: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Unique warehouse code (uppercase alphanumeric)",
    )
    name: str = Field(..., min_length=1, max_length=200, description="Warehouse name")
    warehouse_type: WarehouseTypeEnum = Field(..., description="Facility type")
    geojson_coordinates: dict[str, Any] = Field(
        ..., description="Warehouse boundary polygon (GeoJSON format)"
    )
    active: bool = Field(default=True, description="Active status (soft delete flag)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "GH-001",
                "name": "Main Greenhouse",
                "warehouse_type": "greenhouse",
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
        """Validate warehouse code format.

        Rules:
            - Must be uppercase
            - Alphanumeric with optional - and _

        Args:
            v: Warehouse code to validate

        Returns:
            Validated code (uppercase)

        Raises:
            ValueError: If code format is invalid
        """
        if not v.isupper():
            raise ValueError(f"Warehouse code must be uppercase (got: {v})")

        import re

        if not re.match(r"^[A-Z0-9_-]+$", v):
            raise ValueError(f"Warehouse code must be alphanumeric with optional - or _ (got: {v})")

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


class WarehouseUpdateRequest(BaseModel):
    """Request schema for updating an existing warehouse.

    All fields are optional (partial update supported).

    Attributes:
        code: New warehouse code (optional)
        name: New warehouse name (optional)
        warehouse_type: New facility type (optional)
        geojson_coordinates: New boundary polygon (optional)
        active: New active status (optional)

    Example:
        ```python
        # Partial update (only name)
        request = WarehouseUpdateRequest(name="Updated Greenhouse Name")

        # Multiple fields
        request = WarehouseUpdateRequest(
            name="Updated Name",
            active=False
        )
        ```
    """

    code: str | None = Field(None, min_length=2, max_length=20, description="Warehouse code")
    name: str | None = Field(None, min_length=1, max_length=200, description="Warehouse name")
    warehouse_type: WarehouseTypeEnum | None = Field(None, description="Facility type")
    geojson_coordinates: dict[str, Any] | None = Field(
        None, description="Warehouse boundary polygon (GeoJSON format)"
    )
    active: bool | None = Field(None, description="Active status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Greenhouse Name",
                "active": True,
            }
        }
    )

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str | None) -> str | None:
        """Validate warehouse code format if provided."""
        if v is None:
            return v

        if not v.isupper():
            raise ValueError(f"Warehouse code must be uppercase (got: {v})")

        import re

        if not re.match(r"^[A-Z0-9_-]+$", v):
            raise ValueError(f"Warehouse code must be alphanumeric with optional - or _ (got: {v})")

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


class WarehouseResponse(BaseModel):
    """Response schema for warehouse data.

    Transforms SQLAlchemy Warehouse model to JSON-serializable format.
    PostGIS geometry is converted to GeoJSON standard format.

    Attributes:
        warehouse_id: Primary key
        code: Unique warehouse code
        name: Warehouse name
        warehouse_type: Facility type
        geojson_coordinates: Boundary polygon (GeoJSON format)
        centroid: Center point (GeoJSON format, nullable)
        area_m2: Calculated area in square meters (nullable)
        active: Active status
        created_at: Creation timestamp
        updated_at: Last update timestamp (nullable)

    Example:
        ```python
        # Transform from SQLAlchemy model
        response = WarehouseResponse.from_model(warehouse)

        # JSON serialization (for FastAPI response)
        return response  # FastAPI auto-converts to JSON
        ```
    """

    warehouse_id: int = Field(..., description="Primary key")
    code: str = Field(..., description="Unique warehouse code")
    name: str = Field(..., description="Warehouse name")
    warehouse_type: str = Field(..., description="Facility type")
    geojson_coordinates: dict[str, Any] = Field(
        ..., description="Warehouse boundary (GeoJSON Polygon)"
    )
    centroid: dict[str, Any] | None = Field(None, description="Center point (GeoJSON Point)")
    area_m2: float | None = Field(None, description="Calculated area in square meters")
    active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "warehouse_id": 1,
                "code": "GH-001",
                "name": "Main Greenhouse",
                "warehouse_type": "greenhouse",
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
                "area_m2": 10500.50,
                "active": True,
                "created_at": "2025-10-20T14:30:00Z",
                "updated_at": None,
            }
        },
    )

    @classmethod
    def from_model(cls, warehouse: Warehouse) -> "WarehouseResponse":
        """Transform SQLAlchemy Warehouse model to Pydantic schema.

        Converts PostGIS geometry columns to GeoJSON format using GeoAlchemy2.

        Args:
            warehouse: SQLAlchemy Warehouse instance

        Returns:
            WarehouseResponse with GeoJSON geometry

        Example:
            ```python
            warehouse = await repo.get(123)
            response = WarehouseResponse.from_model(warehouse)
            ```
        """
        from geoalchemy2.shape import to_shape

        # Convert PostGIS geometry to GeoJSON
        geojson = to_shape(warehouse.geojson_coordinates).__geo_interface__

        # Convert centroid if present (nullable)
        centroid = None
        if warehouse.centroid is not None:
            centroid = to_shape(warehouse.centroid).__geo_interface__

        return cls(
            warehouse_id=warehouse.warehouse_id,
            code=warehouse.code,
            name=warehouse.name,
            warehouse_type=warehouse.warehouse_type.value,  # Enum to string
            geojson_coordinates=geojson,
            centroid=centroid,
            area_m2=float(warehouse.area_m2) if warehouse.area_m2 else None,
            active=warehouse.active,
            created_at=warehouse.created_at,
            updated_at=warehouse.updated_at,
        )


class StorageAreaSummary(BaseModel):
    """Summary schema for storage areas (used in WarehouseWithAreasResponse).

    Attributes:
        storage_area_id: Primary key
        code: Unique area code
        name: Area name
        area_type: Area type
        active: Active status
    """

    storage_area_id: int = Field(..., description="Primary key")
    code: str = Field(..., description="Unique area code")
    name: str = Field(..., description="Area name")
    area_type: str = Field(..., description="Area type")
    active: bool = Field(..., description="Active status")

    model_config = ConfigDict(from_attributes=True)


class WarehouseWithAreasResponse(WarehouseResponse):
    """Extended warehouse response including storage areas.

    Inherits all fields from WarehouseResponse and adds storage_areas list.

    Attributes:
        storage_areas: List of storage areas within this warehouse

    Example:
        ```python
        # Get warehouse with areas
        warehouses = await service.get_active_warehouses(include_areas=True)
        # warehouses[0].storage_areas -> list of areas
        ```
    """

    storage_areas: list[StorageAreaSummary] = Field(
        default_factory=list, description="Storage areas within this warehouse"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "warehouse_id": 1,
                "code": "GH-001",
                "name": "Main Greenhouse",
                "warehouse_type": "greenhouse",
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
                "area_m2": 10500.50,
                "active": True,
                "created_at": "2025-10-20T14:30:00Z",
                "updated_at": None,
                "storage_areas": [
                    {
                        "storage_area_id": 1,
                        "code": "AREA-A",
                        "name": "Area A",
                        "area_type": "production",
                        "active": True,
                    },
                    {
                        "storage_area_id": 2,
                        "code": "AREA-B",
                        "name": "Area B",
                        "area_type": "production",
                        "active": True,
                    },
                ],
            }
        },
    )

    @classmethod
    def from_model(cls, warehouse: Warehouse) -> "WarehouseWithAreasResponse":
        """Transform Warehouse model with storage_areas relationship.

        Args:
            warehouse: Warehouse instance with storage_areas loaded

        Returns:
            WarehouseWithAreasResponse with areas list
        """
        # Use parent class method for base fields
        base_response = WarehouseResponse.from_model(warehouse)

        # Add storage areas if present
        storage_areas = []
        if hasattr(warehouse, "storage_areas") and warehouse.storage_areas:
            storage_areas = [
                StorageAreaSummary.model_validate(area) for area in warehouse.storage_areas
            ]

        return cls(**base_response.model_dump(), storage_areas=storage_areas)
