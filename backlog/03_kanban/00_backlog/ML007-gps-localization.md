# [ML007] GPS Localization Service

## Metadata

- **Epic**: epic-007
- **Sprint**: Sprint-02
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Dependencies**: Blocks [ML009], Blocked by [DB003-storage-locations]

## Description

Map GPS coordinates from photo EXIF to storage_location using PostGIS ST_Contains query.

## Acceptance Criteria

- [ ] Extract GPS from EXIF (Pillow)
- [ ] PostGIS query:
  `SELECT id FROM storage_locations WHERE ST_Contains(geojson_coordinates, ST_Point(lon, lat))`
- [ ] Return storage_location_id or NULL
- [ ] Handle missing GPS gracefully

## Implementation

```python
class GPSLocalizationService:
    async def find_location_from_gps(self, lat: float, lon: float) -> Optional[int]:
        query = text("""
            SELECT location_id FROM storage_locations
            WHERE ST_Contains(geojson_coordinates, ST_SetSRID(ST_Point(:lon, :lat), 4326))
            LIMIT 1
        """)
        result = await self.session.execute(query, {'lon': lon, 'lat': lat})
        return result.scalar_one_or_none()
```

## Testing

- Test point-in-polygon with known fixtures
- Coverage ≥80%

---
**Card Created**: 2025-10-09
