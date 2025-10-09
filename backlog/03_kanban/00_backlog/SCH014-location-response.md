# [SCH014] LocationResponse Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/schemas`

## Description

Response schema for storage locations with geospatial data.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class LocationResponse(BaseModel):
      """Response schema for storage location."""

      storage_location_id: int
      code: str
      name: str
      storage_area_id: int
      area_m2: Optional[float]

      # Geospatial
      geojson_coordinates: Optional[dict]  # GeoJSON polygon
      centroid: Optional[dict]  # GeoJSON point

      # Configuration (optional)
      config: Optional[dict] = None

      # Stock summary
      total_plants: Optional[int] = None
      total_batches: Optional[int] = None

      class Config:
          from_attributes = True

      @classmethod
      def from_model(cls, location, include_config: bool = False, include_stock: bool = False):
          from geoalchemy2.shape import to_shape
          import json

          data = {
              "storage_location_id": location.storage_location_id,
              "code": location.code,
              "name": location.name,
              "storage_area_id": location.storage_area_id,
              "area_m2": location.area_m2
          }

          # Convert PostGIS geometry to GeoJSON
          if location.geojson_coordinates:
              geom = to_shape(location.geojson_coordinates)
              data["geojson_coordinates"] = json.loads(json.dumps(geom.__geo_interface__))

          if location.centroid:
              centroid_geom = to_shape(location.centroid)
              data["centroid"] = json.loads(json.dumps(centroid_geom.__geo_interface__))

          if include_config and location.config:
              data["config"] = {
                  "product_id": location.config.product_id,
                  "packaging_catalog_id": location.config.packaging_catalog_id
              }

          if include_stock:
              # Calculate from stock_batches
              data["total_plants"] = sum(b.current_quantity for b in location.stock_batches)
              data["total_batches"] = len(location.stock_batches)

          return cls(**data)
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
