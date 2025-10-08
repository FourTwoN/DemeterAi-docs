# Warehouse Map Overview - Geographic View with PostGIS Polygons

**Version:** 1.0.0
**Date:** 2025-10-08
**System:** DemeterAI Map Warehouse Views
**Parent Flow:** 00_comprehensive_view

## Purpose

This subflow details the **geographic map overview** displaying all warehouses as PostGIS polygons with summary metrics, enabling users to visualize facility locations and navigate to internal warehouse views.

## Scope

- **Level**: Detailed subflow (Level 1 of 4)
- **Audience**: Developers, UX designers, GIS specialists
- **Detail**: PostGIS polygon rendering, bulk data loading, map interactions
- **Technology**: React, Leaflet, PostGIS, PostgreSQL

## What It Represents

The warehouse map overview is the **entry point** of the map navigation system:

1. **User opens app** → Bulk load all warehouse data
2. **Map renders** all warehouses as colored PostGIS polygons
3. **Summary metrics** displayed per warehouse (claros, naves count)
4. **User clicks polygon** → Navigate to warehouse internal view
5. **Data cached** for instant navigation between views

## Key Features

### Geographic Visualization
- **PostGIS polygons**: Warehouse boundaries rendered from `geojson_coordinates` column
- **Color coding**: Different colors for warehouse types (greenhouse, shadehouse, etc.)
- **Hover tooltips**: Show warehouse name and quick metrics
- **Zoom/pan controls**: Standard map navigation

### Summary Metrics
Each warehouse polygon displays:
- **Claros count**: Total storage_locations in warehouse
- **Naves count**: Total storage_areas in warehouse
- **Total plants**: Aggregate from latest photo sessions
- **Last photo date**: Most recent photo timestamp

### Performance Optimization
- **Bulk load**: Single API call loads all warehouses + storage data
- **Materialized view**: Pre-aggregated metrics via `mv_warehouse_summary`
- **Client cache**: Data stored in frontend state (Redux/Zustand/Context)
- **GeoJSON caching**: Polygon coordinates cached (rarely change)

## Database Schema

### warehouses Table
```sql
CREATE TABLE warehouses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- greenhouse|shadehouse|open_field|tunnel
    geojson_coordinates GEOMETRY(POLYGON, 4326) NOT NULL,  -- PostGIS
    centroid GEOMETRY(POINT, 4326) GENERATED ALWAYS AS (ST_Centroid(geojson_coordinates)) STORED,
    area_m2 NUMERIC(10,2) GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_warehouses_geojson ON warehouses USING GIST (geojson_coordinates);
CREATE INDEX idx_warehouses_centroid ON warehouses USING GIST (centroid);
CREATE INDEX idx_warehouses_active ON warehouses(active);
CREATE INDEX idx_warehouses_type ON warehouses(type);
```

**Key fields:**
- `geojson_coordinates`: PostGIS GEOMETRY(POLYGON, 4326) - warehouse boundary in WGS84
- `centroid`: Auto-generated center point for labels and centering map
- `area_m2`: Auto-calculated area in square meters using PostGIS geography
- `type`: Warehouse classification for color coding

### Materialized View: mv_warehouse_summary
Pre-aggregated metrics for fast map rendering.

```sql
CREATE MATERIALIZED VIEW mv_warehouse_summary AS
SELECT
    w.id AS warehouse_id,
    w.code AS warehouse_code,
    w.name AS warehouse_name,
    w.type AS warehouse_type,
    w.geojson_coordinates,
    w.centroid,
    w.area_m2,
    w.active,
    COUNT(DISTINCT sa.id) AS naves_count,
    COUNT(DISTINCT sl.id) AS claros_count,
    SUM(COALESCE(pps.total_detected, 0)) AS total_plants,
    MAX(pps.created_at) AS last_photo_date
FROM warehouses w
LEFT JOIN storage_areas sa ON sa.warehouse_id = w.id
LEFT JOIN storage_locations sl ON sl.storage_area_id = sa.id
LEFT JOIN photo_processing_sessions pps ON pps.storage_location_id = sl.id
WHERE w.active = true
GROUP BY w.id, w.code, w.name, w.type, w.geojson_coordinates, w.centroid, w.area_m2, w.active;

-- Indexes
CREATE UNIQUE INDEX idx_mv_warehouse_summary_id ON mv_warehouse_summary(warehouse_id);
CREATE INDEX idx_mv_warehouse_summary_geojson ON mv_warehouse_summary USING GIST (geojson_coordinates);
CREATE INDEX idx_mv_warehouse_summary_type ON mv_warehouse_summary(warehouse_type);
```

**Refresh strategy:**
```sql
-- Refresh every 5 minutes via pg_cron
SELECT cron.schedule(
    'refresh-warehouse-summary',
    '*/5 * * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_warehouse_summary'
);

-- Manual refresh on demand
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_warehouse_summary;
```

## PostGIS Queries

### Query 1: Get All Warehouses as GeoJSON
Used by bulk-load endpoint to fetch all warehouse polygons.

```sql
SELECT
    ws.warehouse_id,
    ws.warehouse_code,
    ws.warehouse_name,
    ws.warehouse_type,
    ST_AsGeoJSON(ws.geojson_coordinates)::json AS geojson,
    ST_AsGeoJSON(ws.centroid)::json AS centroid,
    ws.area_m2,
    ws.active,
    ws.naves_count,
    ws.claros_count,
    ws.total_plants,
    ws.last_photo_date
FROM mv_warehouse_summary ws
WHERE ws.active = true
ORDER BY ws.warehouse_name;
```

**Example output:**
```json
{
  "warehouse_id": 1,
  "warehouse_code": "WH-001",
  "warehouse_name": "Warehouse A",
  "warehouse_type": "greenhouse",
  "geojson": {
    "type": "Polygon",
    "coordinates": [
      [
        [-58.381592, -34.603722],
        [-58.380592, -34.603722],
        [-58.380592, -34.604722],
        [-58.381592, -34.604722],
        [-58.381592, -34.603722]
      ]
    ]
  },
  "centroid": {
    "type": "Point",
    "coordinates": [-58.381092, -34.604222]
  },
  "area_m2": 1200.50,
  "active": true,
  "naves_count": 5,
  "claros_count": 120,
  "total_plants": 14500,
  "last_photo_date": "2025-10-08T10:30:00Z"
}
```

### Query 2: Get Warehouses Within Map Bounds (Viewport Filtering)
For future optimization when there are many warehouses.

```sql
SELECT
    ws.warehouse_id,
    ws.warehouse_code,
    ws.warehouse_name,
    ws.warehouse_type,
    ST_AsGeoJSON(ws.geojson_coordinates)::json AS geojson,
    ST_AsGeoJSON(ws.centroid)::json AS centroid,
    ws.area_m2,
    ws.naves_count,
    ws.claros_count,
    ws.total_plants,
    ws.last_photo_date
FROM mv_warehouse_summary ws
WHERE ST_Intersects(
    ws.geojson_coordinates,
    ST_MakeEnvelope($1, $2, $3, $4, 4326)  -- minLon, minLat, maxLon, maxLat
)
AND ws.active = true;
```

**Usage:**
```javascript
// Frontend calculates map bounds
const bounds = map.getBounds();
const params = {
    minLon: bounds.getWest(),
    minLat: bounds.getSouth(),
    maxLon: bounds.getEast(),
    maxLat: bounds.getNorth()
};

// API call with bounds
fetch(`/api/v1/warehouses/in-bounds?${new URLSearchParams(params)}`);
```

### Query 3: Calculate Warehouse Centroid and Area
For creating new warehouses or updating existing ones.

```sql
-- Insert new warehouse with auto-calculated centroid and area
INSERT INTO warehouses (code, name, type, geojson_coordinates)
VALUES (
    'WH-002',
    'Warehouse B',
    'shadehouse',
    ST_GeomFromGeoJSON('{
        "type": "Polygon",
        "coordinates": [[
            [-58.381, -34.603],
            [-58.380, -34.603],
            [-58.380, -34.604],
            [-58.381, -34.604],
            [-58.381, -34.603]
        ]]
    }')
);

-- Centroid and area_m2 are auto-generated by PostgreSQL
```

## API Endpoints

### GET /api/v1/map/bulk-load
Bulk load all warehouse and storage data for initial app load.

**Request:**
```http
GET /api/v1/map/bulk-load HTTP/1.1
Authorization: Bearer <token>
```

**Query Parameters:**
- None (loads all active warehouses)

**Response:**
```json
{
  "warehouses": [
    {
      "id": 1,
      "code": "WH-001",
      "name": "Warehouse A",
      "type": "greenhouse",
      "geojson": {
        "type": "Polygon",
        "coordinates": [[...]]
      },
      "centroid": {
        "type": "Point",
        "coordinates": [-58.3811, -34.6042]
      },
      "area_m2": 1200.50,
      "metrics": {
        "naves_count": 5,
        "claros_count": 120,
        "total_plants": 14500,
        "last_photo_date": "2025-10-08T10:30:00Z"
      }
    }
  ],
  "storage_areas": [...],
  "storage_locations": [...],
  "metadata": {
    "total_warehouses": 1,
    "total_storage_areas": 5,
    "total_storage_locations": 120,
    "cache_timestamp": "2025-10-08T14:30:00Z",
    "refresh_interval_minutes": 10
  }
}
```

**Performance:**
- Response time: < 1000ms
- Payload size: ~500KB - 2MB (compressed)
- Cache: Redis TTL 10 minutes
- Compression: GZIP enabled

**Backend Implementation (Python/FastAPI):**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_AsGeoJSON

router = APIRouter()

@router.get("/map/bulk-load")
async def bulk_load_map_data(db: Session = Depends(get_db)):
    """
    Bulk load all warehouse and storage data for map visualization.

    Returns:
        - All warehouses with PostGIS polygons
        - All storage_areas
        - All storage_locations with preview data
    """
    # Query 1: Get all warehouses from materialized view
    warehouses_query = db.execute(text("""
        SELECT
            ws.warehouse_id,
            ws.warehouse_code,
            ws.warehouse_name,
            ws.warehouse_type,
            ST_AsGeoJSON(ws.geojson_coordinates)::json AS geojson,
            ST_AsGeoJSON(ws.centroid)::json AS centroid,
            ws.area_m2,
            ws.naves_count,
            ws.claros_count,
            ws.total_plants,
            ws.last_photo_date
        FROM mv_warehouse_summary ws
        WHERE ws.active = true
        ORDER BY ws.warehouse_name
    """))

    warehouses = [
        {
            "id": row.warehouse_id,
            "code": row.warehouse_code,
            "name": row.warehouse_name,
            "type": row.warehouse_type,
            "geojson": row.geojson,
            "centroid": row.centroid,
            "area_m2": float(row.area_m2) if row.area_m2 else 0,
            "metrics": {
                "naves_count": row.naves_count,
                "claros_count": row.claros_count,
                "total_plants": row.total_plants,
                "last_photo_date": row.last_photo_date.isoformat() if row.last_photo_date else None
            }
        }
        for row in warehouses_query
    ]

    # Query 2: Get all storage_areas (see 02_warehouse_internal_structure.md)
    storage_areas = get_all_storage_areas(db)

    # Query 3: Get all storage_locations with preview data (see 03_storage_location_preview.md)
    storage_locations = get_all_storage_locations_preview(db)

    return {
        "warehouses": warehouses,
        "storage_areas": storage_areas,
        "storage_locations": storage_locations,
        "metadata": {
            "total_warehouses": len(warehouses),
            "total_storage_areas": len(storage_areas),
            "total_storage_locations": len(storage_locations),
            "cache_timestamp": datetime.now().isoformat(),
            "refresh_interval_minutes": 10
        }
    }
```

**Redis Caching:**
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@router.get("/map/bulk-load")
async def bulk_load_map_data(db: Session = Depends(get_db)):
    # Check cache first
    cache_key = "cache:map:bulk-load"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # Fetch from database
    result = fetch_bulk_data(db)

    # Cache for 10 minutes
    redis_client.setex(
        cache_key,
        600,  # 10 minutes
        json.dumps(result)
    )

    return result
```

### GET /api/v1/warehouses/in-bounds (Future Optimization)
Fetch warehouses within map viewport bounds.

**Request:**
```http
GET /api/v1/warehouses/in-bounds?minLon=-58.382&minLat=-34.605&maxLon=-58.380&maxLat=-34.603 HTTP/1.1
Authorization: Bearer <token>
```

**Response:**
Same as bulk-load but filtered to viewport.

**Use case:** When there are 100+ warehouses, only load visible ones.

## Frontend Implementation (React + Leaflet)

### Component: MapOverview
Main map component rendering warehouse polygons.

```typescript
import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polygon, Popup, Tooltip, useMap } from 'react-leaflet';
import { LatLngBounds } from 'leaflet';
import { useNavigate } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';

interface WarehouseMetrics {
  naves_count: number;
  claros_count: number;
  total_plants: number;
  last_photo_date: string | null;
}

interface WarehouseSummary {
  id: number;
  code: string;
  name: string;
  type: 'greenhouse' | 'shadehouse' | 'open_field' | 'tunnel';
  geojson: GeoJSON.Polygon;
  centroid: GeoJSON.Point;
  area_m2: number;
  metrics: WarehouseMetrics;
}

interface BulkLoadResponse {
  warehouses: WarehouseSummary[];
  storage_areas: any[];
  storage_locations: any[];
  metadata: {
    total_warehouses: number;
    total_storage_areas: number;
    total_storage_locations: number;
    cache_timestamp: string;
    refresh_interval_minutes: number;
  };
}

export const MapOverview: React.FC = () => {
  const [warehouses, setWarehouses] = useState<WarehouseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Bulk load all data on component mount
    const fetchData = async () => {
      try {
        const response = await fetch('/api/v1/map/bulk-load', {
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: BulkLoadResponse = await response.json();

        setWarehouses(data.warehouses);

        // Store storage_locations in global state for warehouse internal view
        globalState.setStorageAreas(data.storage_areas);
        globalState.setStorageLocations(data.storage_locations);

        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const getWarehouseColor = (type: string): string => {
    switch (type) {
      case 'greenhouse':
        return '#4CAF50';  // Green
      case 'shadehouse':
        return '#2196F3';  // Blue
      case 'open_field':
        return '#FFC107';  // Amber
      case 'tunnel':
        return '#9C27B0';  // Purple
      default:
        return '#757575';  // Grey
    }
  };

  const getWarehouseTypeLabel = (type: string): string => {
    switch (type) {
      case 'greenhouse':
        return 'Greenhouse';
      case 'shadehouse':
        return 'Shadehouse';
      case 'open_field':
        return 'Open Field';
      case 'tunnel':
        return 'Tunnel';
      default:
        return type;
    }
  };

  const handleWarehouseClick = (warehouseId: number) => {
    // Navigate to warehouse internal view
    navigate(`/warehouses/${warehouseId}/internal`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="spinner-border animate-spin inline-block w-8 h-8 border-4 rounded-full" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2 text-gray-600">Loading warehouse map...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="alert alert-error">
          <p>Error loading map: {error}</p>
          <button onClick={() => window.location.reload()} className="btn btn-sm">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Calculate map bounds from all warehouses
  const bounds = warehouses.length > 0
    ? warehouses.map(w => [
        w.centroid.coordinates[1],  // lat
        w.centroid.coordinates[0]   // lon
      ])
    : [[-34.603722, -58.381592]];

  return (
    <div className="map-overview-container">
      <div className="map-header bg-white shadow p-4 mb-2">
        <h1 className="text-2xl font-bold">Warehouse Map Overview</h1>
        <p className="text-gray-600">
          {warehouses.length} warehouses · Click a warehouse to view internal structure
        </p>
        <div className="legend flex gap-4 mt-2">
          {['greenhouse', 'shadehouse', 'open_field', 'tunnel'].map(type => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: getWarehouseColor(type) }}
              />
              <span className="text-sm">{getWarehouseTypeLabel(type)}</span>
            </div>
          ))}
        </div>
      </div>

      <MapContainer
        bounds={bounds}
        style={{ height: 'calc(100vh - 150px)', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {warehouses.map(warehouse => {
          // Convert GeoJSON coordinates to Leaflet LatLng format
          const positions = warehouse.geojson.coordinates[0].map(coord => [
            coord[1],  // lat
            coord[0]   // lon
          ]);

          return (
            <Polygon
              key={warehouse.id}
              positions={positions}
              pathOptions={{
                color: getWarehouseColor(warehouse.type),
                fillColor: getWarehouseColor(warehouse.type),
                fillOpacity: 0.3,
                weight: 2
              }}
              eventHandlers={{
                click: () => handleWarehouseClick(warehouse.id),
                mouseover: (e) => {
                  e.target.setStyle({
                    fillOpacity: 0.5,
                    weight: 3
                  });
                },
                mouseout: (e) => {
                  e.target.setStyle({
                    fillOpacity: 0.3,
                    weight: 2
                  });
                }
              }}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={0.9}>
                <div>
                  <strong>{warehouse.name}</strong>
                  <br />
                  <span className="text-xs text-gray-600">{warehouse.code}</span>
                </div>
              </Tooltip>

              <Popup>
                <div className="warehouse-popup" style={{ minWidth: '250px' }}>
                  <h3 className="text-lg font-bold mb-2">{warehouse.name}</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-600">Type:</span>
                      <br />
                      <strong>{getWarehouseTypeLabel(warehouse.type)}</strong>
                    </div>
                    <div>
                      <span className="text-gray-600">Area:</span>
                      <br />
                      <strong>{warehouse.area_m2.toFixed(2)} m²</strong>
                    </div>
                    <div>
                      <span className="text-gray-600">Naves:</span>
                      <br />
                      <strong>{warehouse.metrics.naves_count}</strong>
                    </div>
                    <div>
                      <span className="text-gray-600">Claros:</span>
                      <br />
                      <strong>{warehouse.metrics.claros_count}</strong>
                    </div>
                    <div>
                      <span className="text-gray-600">Total Plants:</span>
                      <br />
                      <strong>{warehouse.metrics.total_plants?.toLocaleString() || 0}</strong>
                    </div>
                  </div>
                  {warehouse.metrics.last_photo_date && (
                    <div className="mt-2 text-xs text-gray-600">
                      Last photo: {new Date(warehouse.metrics.last_photo_date).toLocaleDateString()}
                    </div>
                  )}
                  <button
                    onClick={() => handleWarehouseClick(warehouse.id)}
                    className="btn btn-primary btn-sm w-full mt-3"
                  >
                    View Internal Structure
                  </button>
                </div>
              </Popup>
            </Polygon>
          );
        })}
      </MapContainer>
    </div>
  );
};
```

### Global State Management (Zustand Example)
Store bulk-loaded data for use in other components.

```typescript
import create from 'zustand';

interface MapState {
  warehouses: WarehouseSummary[];
  storageAreas: any[];
  storageLocations: any[];
  cacheTimestamp: string | null;
  setWarehouses: (warehouses: WarehouseSummary[]) => void;
  setStorageAreas: (areas: any[]) => void;
  setStorageLocations: (locations: any[]) => void;
  clearCache: () => void;
}

export const useMapStore = create<MapState>((set) => ({
  warehouses: [],
  storageAreas: [],
  storageLocations: [],
  cacheTimestamp: null,
  setWarehouses: (warehouses) => set({ warehouses, cacheTimestamp: new Date().toISOString() }),
  setStorageAreas: (storageAreas) => set({ storageAreas }),
  setStorageLocations: (storageLocations) => set({ storageLocations }),
  clearCache: () => set({
    warehouses: [],
    storageAreas: [],
    storageLocations: [],
    cacheTimestamp: null
  })
}));
```

## Performance Metrics

### Response Time
- **Target**: < 1000ms for bulk-load
- **Actual**: 500-800ms with materialized view + Redis cache
- **Factors**: Database query (200ms), JSON serialization (100ms), network (200ms)

### Payload Size
- **Uncompressed**: ~2MB for 10 warehouses with 1000 storage_locations
- **Compressed (GZIP)**: ~500KB (75% reduction)
- **Per warehouse**: ~50KB average

### Cache Hit Rate
- **Redis cache**: 95%+ hit rate during 10-minute window
- **Browser cache**: Stored in global state for session duration
- **Invalidation**: On materialized view refresh or manual trigger

## User Experience

### Loading State
1. **User opens app** → "Loading warehouse map..." spinner (1-2 seconds)
2. **Map renders** → All polygons appear at once
3. **Interactions enabled** → User can click/hover immediately

### Error Handling
- **Network error**: Retry button with error message
- **Empty data**: "No warehouses found" message
- **Timeout**: Show partial data if some requests succeed

### Navigation Flow
1. **User views map** → All warehouses visible
2. **User clicks warehouse** → Instant navigation (data cached)
3. **User returns to map** → Map state preserved

## Related Subflows

- **02_warehouse_internal_structure.md**: Next level - storage areas and preview cards
- **03_storage_location_preview.md**: Preview card component details
- **04_storage_location_detail.md**: Full detail view on click
- **05_historical_timeline.md**: Historical tracking for storage locations

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial warehouse map overview subflow |

---

**Notes:**
- PostGIS SRID 4326 (WGS84) is standard for GPS coordinates
- Leaflet expects coordinates in [lat, lon] format (reversed from GeoJSON [lon, lat])
- Materialized view refresh every 5 minutes balances freshness and performance
- Bulk load strategy ensures instant navigation between views
- Color coding provides quick visual identification of warehouse types
