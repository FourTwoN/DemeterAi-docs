# Warehouse Internal Structure - Storage Areas and Preview Cards

**Version:** 1.0.0
**Date:** 2025-10-08
**System:** DemeterAI Map Warehouse Views
**Parent Flow:** 00_comprehensive_view

## Purpose

This subflow details the **warehouse internal structure view** displaying storage areas (canteros:
Norte, Sur, Este, Oeste, Centro) and all storage_locations as preview cards with key metrics.

## Scope

- **Level**: Detailed subflow (Level 2 of 4)
- **Audience**: Developers, UX designers
- **Detail**: Storage areas organization, preview cards grid, filtering
- **Technology**: React, already-loaded data from bulk-load

## What It Represents

The warehouse internal structure view allows users to:

1. **Navigate from map** → Click warehouse polygon
2. **View storage areas** → Display canteros (N, S, E, W, C)
3. **Browse storage_locations** → Grid of preview cards
4. **Filter by cantero** → Show only specific storage area
5. **Click preview card** → Navigate to full detail view (Level 3)

## Key Features

### Storage Areas (Canteros)

- **Position-based organization**: Norte, Sur, Este, Oeste, Centro
- **Visual representation**: Cards or map sections
- **Filter buttons**: Click to show only storage_locations in that area
- **Count badges**: Show number of claros per cantero

### Preview Cards for Storage Locations

Each card displays:

- **Thumbnail**: Last photo thumbnail (300x300px from S3)
- **Quantity**: Current plant count with trend indicator (↑↓)
- **Maceta type**: Primary container type (8cm, 10cm, etc.)
- **Current value**: Monetary value (quantity × price)
- **Potential value**: Estimated future value (+30% growth)
- **Last updated**: Timestamp of última foto
- **Category breakdown**: Cactus, suculenta, injerto counts
- **Status badge**: Green (healthy), yellow (warning), red (error)

### Performance Features

- **No API call needed**: Data already loaded from bulk-load
- **Client-side filtering**: Instant cantero filtering
- **Lazy rendering**: Virtualization for large grids (100+ cards)
- **Cached thumbnails**: Presigned S3 URLs from bulk-load

## Database Schema

### storage_areas Table

```sql
CREATE TABLE storage_areas (
    id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    position VARCHAR(10) NOT NULL,  -- N|S|E|W|C (Norte|Sur|Este|Oeste|Centro)
    geojson_coordinates GEOMETRY(POLYGON, 4326),  -- PostGIS, nullable
    centroid GEOMETRY(POINT, 4326) GENERATED ALWAYS AS (ST_Centroid(geojson_coordinates)) STORED,
    area_m2 NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT chk_position CHECK (position IN ('N', 'S', 'E', 'W', 'C'))
);

-- Indexes
CREATE INDEX idx_storage_areas_warehouse ON storage_areas(warehouse_id);
CREATE INDEX idx_storage_areas_geojson ON storage_areas USING GIST (geojson_coordinates);
CREATE INDEX idx_storage_areas_position ON storage_areas(warehouse_id, position);
```

### storage_locations Table

```sql
CREATE TABLE storage_locations (
    id SERIAL PRIMARY KEY,
    storage_area_id INTEGER NOT NULL REFERENCES storage_areas(id) ON DELETE CASCADE,
    code VARCHAR(50) UNIQUE NOT NULL,
    qr_code VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    description TEXT,
    geojson_coordinates GEOMETRY(POLYGON, 4326),  -- PostGIS, nullable
    centroid GEOMETRY(POINT, 4326) GENERATED ALWAYS AS (ST_Centroid(geojson_coordinates)) STORED,
    area_m2 NUMERIC(10,2),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_storage_locations_area ON storage_locations(storage_area_id);
CREATE INDEX idx_storage_locations_geojson ON storage_locations USING GIST (geojson_coordinates);
CREATE INDEX idx_storage_locations_active ON storage_locations(active);
CREATE INDEX idx_storage_locations_qr ON storage_locations(qr_code);
CREATE INDEX idx_storage_locations_code ON storage_locations(code);
```

### Materialized View: mv_storage_location_preview

Pre-aggregated preview data for all storage_locations.

```sql
CREATE MATERIALIZED VIEW mv_storage_location_preview AS
WITH latest_sessions AS (
    SELECT DISTINCT ON (storage_location_id)
        storage_location_id,
        session_id,
        total_detected,
        total_estimated,
        category_counts,
        created_at AS last_photo_date,
        processed_image_id,
        status,
        error_message
    FROM photo_processing_sessions
    WHERE storage_location_id IS NOT NULL
    ORDER BY storage_location_id, created_at DESC
),
previous_sessions AS (
    SELECT DISTINCT ON (pps.storage_location_id)
        pps.storage_location_id,
        pps.total_detected AS previous_quantity
    FROM photo_processing_sessions pps
    INNER JOIN latest_sessions ls ON ls.storage_location_id = pps.storage_location_id
    WHERE pps.status = 'completed'
        AND pps.created_at < ls.last_photo_date
    ORDER BY pps.storage_location_id, pps.created_at DESC
),
stock_summary AS (
    SELECT
        current_storage_bin_id AS storage_location_id,
        SUM(quantity_current) AS current_quantity,
        SUM(quantity_current * cost_per_unit) AS current_value,
        AVG(quality_score) AS avg_quality,
        JSONB_OBJECT_AGG(
            COALESCE(pc.name, 'unknown'),
            COUNT(sb.id)
        ) FILTER (WHERE pc.name IS NOT NULL) AS maceta_distribution
    FROM stock_batches sb
    LEFT JOIN packaging_catalog pc ON pc.id = sb.packaging_catalog_id
    GROUP BY current_storage_bin_id
)
SELECT
    sl.id AS storage_location_id,
    sl.code AS storage_location_code,
    sl.name AS storage_location_name,
    sl.storage_area_id,
    sa.warehouse_id,
    sa.position AS cantero_position,
    sa.name AS cantero_name,
    ls.session_id AS last_session_id,
    ls.last_photo_date,
    ls.processed_image_id,
    ls.status AS last_session_status,
    ls.error_message,
    COALESCE(ls.total_detected, 0) AS current_quantity,
    COALESCE(ps.previous_quantity, 0) AS previous_quantity,
    COALESCE(ls.total_detected, 0) - COALESCE(ps.previous_quantity, 0) AS quantity_change,
    ls.category_counts,
    COALESCE(ss.current_value, 0) AS current_value,
    COALESCE(ss.current_value * 1.3, 0) AS potential_value,  -- 30% growth estimate
    ss.avg_quality AS quality_score,
    ss.maceta_distribution,
    sl.active
FROM storage_locations sl
INNER JOIN storage_areas sa ON sa.id = sl.storage_area_id
LEFT JOIN latest_sessions ls ON ls.storage_location_id = sl.id
LEFT JOIN previous_sessions ps ON ps.storage_location_id = sl.id
LEFT JOIN stock_summary ss ON ss.storage_location_id = sl.id
WHERE sl.active = true;

-- Indexes
CREATE UNIQUE INDEX idx_mv_location_preview_id ON mv_storage_location_preview(storage_location_id);
CREATE INDEX idx_mv_location_preview_warehouse ON mv_storage_location_preview(warehouse_id);
CREATE INDEX idx_mv_location_preview_area ON mv_storage_location_preview(storage_area_id);
CREATE INDEX idx_mv_location_preview_date ON mv_storage_location_preview(last_photo_date DESC NULLS LAST);
CREATE INDEX idx_mv_location_preview_position ON mv_storage_location_preview(warehouse_id, cantero_position);
```

**Refresh strategy:**

```sql
-- Refresh every 10 minutes via pg_cron
SELECT cron.schedule(
    'refresh-location-preview',
    '*/10 * * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_storage_location_preview'
);

-- Manual refresh
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_storage_location_preview;
```

## Data Already Loaded from Bulk-Load

The `/api/v1/map/bulk-load` endpoint returns:

### storage_areas Array

```json
{
  "storage_areas": [
    {
      "id": 1,
      "warehouse_id": 1,
      "code": "WH-001-N",
      "name": "Norte",
      "position": "N",
      "area_m2": 250.00,
      "storage_locations_count": 24
    },
    {
      "id": 2,
      "warehouse_id": 1,
      "code": "WH-001-S",
      "name": "Sur",
      "position": "S",
      "area_m2": 250.00,
      "storage_locations_count": 24
    }
  ]
}
```

### storage_locations Array

```json
{
  "storage_locations": [
    {
      "id": 1,
      "storage_area_id": 1,
      "warehouse_id": 1,
      "code": "WH-001-N-001",
      "name": "Rack 1 Shelf 1",
      "cantero_position": "N",
      "cantero_name": "Norte",
      "preview": {
        "current_quantity": 120,
        "previous_quantity": 115,
        "quantity_change": 5,
        "current_value": 1200.00,
        "potential_value": 1560.00,
        "quality_score": 85.5,
        "last_photo_date": "2025-10-08T10:30:00Z",
        "last_photo_thumbnail_url": "https://s3.../thumbnails/uuid-1.jpg",
        "maceta_primary": "10cm",
        "maceta_distribution": {
          "8cm": 30,
          "10cm": 70,
          "12cm": 20
        },
        "category_counts": {
          "cactus": 50,
          "suculenta": 40,
          "injerto": 30
        },
        "status": "completed",
        "error_message": null
      }
    }
  ]
}
```

## Frontend Implementation

### Component: WarehouseInternalView

Main component for warehouse internal structure.

```typescript
import React, { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMapStore } from '../stores/mapStore';
import { StorageLocationPreviewCard } from './StorageLocationPreviewCard';
import { FixedSizeGrid as Grid } from 'react-window';

interface StorageArea {
  id: number;
  warehouse_id: number;
  code: string;
  name: string;
  position: 'N' | 'S' | 'E' | 'W' | 'C';
  area_m2: number;
  storage_locations_count: number;
}

interface StorageLocationPreview {
  id: number;
  storage_area_id: number;
  warehouse_id: number;
  code: string;
  name: string;
  cantero_position: 'N' | 'S' | 'E' | 'W' | 'C';
  cantero_name: string;
  preview: {
    current_quantity: number;
    previous_quantity: number;
    quantity_change: number;
    current_value: number;
    potential_value: number;
    quality_score: number;
    last_photo_date: string;
    last_photo_thumbnail_url: string;
    maceta_primary: string;
    maceta_distribution: Record<string, number>;
    category_counts: Record<string, number>;
    status: string;
    error_message: string | null;
  };
}

type CanteroPosition = 'N' | 'S' | 'E' | 'W' | 'C' | null;

export const WarehouseInternalView: React.FC = () => {
  const { warehouseId } = useParams<{ warehouseId: string }>();
  const navigate = useNavigate();
  const [selectedCantero, setSelectedCantero] = useState<CanteroPosition>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'quantity' | 'value' | 'updated'>('name');

  // Get data from global state (already loaded in MapOverview)
  const { warehouses, storageAreas, storageLocations } = useMapStore();

  // Get current warehouse
  const warehouse = useMemo(() => {
    return warehouses.find(w => w.id === parseInt(warehouseId));
  }, [warehouses, warehouseId]);

  // Get storage areas for this warehouse
  const warehouseStorageAreas = useMemo(() => {
    return storageAreas.filter(sa => sa.warehouse_id === parseInt(warehouseId));
  }, [storageAreas, warehouseId]);

  // Get storage locations for this warehouse
  const warehouseStorageLocations = useMemo(() => {
    return storageLocations.filter(sl => sl.warehouse_id === parseInt(warehouseId));
  }, [storageLocations, warehouseId]);

  // Filter by cantero and search
  const filteredLocations = useMemo(() => {
    let filtered = warehouseStorageLocations;

    // Filter by selected cantero
    if (selectedCantero) {
      filtered = filtered.filter(loc => loc.cantero_position === selectedCantero);
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(loc =>
        loc.code.toLowerCase().includes(term) ||
        loc.name.toLowerCase().includes(term)
      );
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'quantity':
          return (b.preview?.current_quantity || 0) - (a.preview?.current_quantity || 0);
        case 'value':
          return (b.preview?.current_value || 0) - (a.preview?.current_value || 0);
        case 'updated':
          const dateA = a.preview?.last_photo_date ? new Date(a.preview.last_photo_date).getTime() : 0;
          const dateB = b.preview?.last_photo_date ? new Date(b.preview.last_photo_date).getTime() : 0;
          return dateB - dateA;
        default:
          return 0;
      }
    });

    return filtered;
  }, [warehouseStorageLocations, selectedCantero, searchTerm, sortBy]);

  // Count storage locations per cantero
  const canteroCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    warehouseStorageLocations.forEach(loc => {
      counts[loc.cantero_position] = (counts[loc.cantero_position] || 0) + 1;
    });
    return counts;
  }, [warehouseStorageLocations]);

  const getCanteroLabel = (position: string): string => {
    switch (position) {
      case 'N': return 'Norte';
      case 'S': return 'Sur';
      case 'E': return 'Este';
      case 'W': return 'Oeste';
      case 'C': return 'Centro';
      default: return position;
    }
  };

  const getCanteroColor = (position: string): string => {
    switch (position) {
      case 'N': return 'bg-blue-500';
      case 'S': return 'bg-red-500';
      case 'E': return 'bg-yellow-500';
      case 'W': return 'bg-green-500';
      case 'C': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const handleLocationClick = (locationId: number) => {
    navigate(`/storage-locations/${locationId}/detail`);
  };

  if (!warehouse) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-xl text-gray-600">Warehouse not found</p>
          <button onClick={() => navigate('/map')} className="btn btn-primary mt-4">
            Back to Map
          </button>
        </div>
      </div>
    );
  }

  const canteroOptions: CanteroPosition[] = ['N', 'S', 'E', 'W', 'C'];

  return (
    <div className="warehouse-internal-view">
      {/* Header */}
      <header className="bg-white shadow p-4 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate('/map')}
              className="text-blue-600 hover:text-blue-800 mb-2 flex items-center gap-1"
            >
              ← Back to Map
            </button>
            <h1 className="text-2xl font-bold">{warehouse.name}</h1>
            <p className="text-gray-600">
              {warehouseStorageAreas.length} storage areas ·{' '}
              {warehouseStorageLocations.length} storage locations
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">Total Plants</p>
            <p className="text-3xl font-bold text-green-600">
              {warehouseStorageLocations.reduce((sum, loc) =>
                sum + (loc.preview?.current_quantity || 0), 0
              ).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Storage Areas Filter */}
        <div className="cantero-filter flex gap-2 mt-4">
          <button
            className={`btn btn-sm ${!selectedCantero ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setSelectedCantero(null)}
          >
            All ({warehouseStorageLocations.length})
          </button>
          {canteroOptions.map(cantero => (
            <button
              key={cantero}
              className={`btn btn-sm ${selectedCantero === cantero ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setSelectedCantero(cantero)}
            >
              <span className={`w-3 h-3 rounded-full ${getCanteroColor(cantero)} inline-block mr-1`} />
              {getCanteroLabel(cantero)} ({canteroCounts[cantero] || 0})
            </button>
          ))}
        </div>

        {/* Search and Sort */}
        <div className="flex gap-4 mt-4">
          <input
            type="text"
            placeholder="Search by code or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input input-bordered flex-1"
          />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="select select-bordered"
          >
            <option value="name">Sort by Name</option>
            <option value="quantity">Sort by Quantity</option>
            <option value="value">Sort by Value</option>
            <option value="updated">Sort by Last Updated</option>
          </select>
        </div>
      </header>

      {/* Storage Locations Grid */}
      <div className="storage-locations-grid p-4">
        <p className="text-sm text-gray-600 mb-4">
          Showing {filteredLocations.length} storage location(s)
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredLocations.map(location => (
            <StorageLocationPreviewCard
              key={location.id}
              location={location}
              onClick={() => handleLocationClick(location.id)}
            />
          ))}
        </div>

        {filteredLocations.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No storage locations found</p>
            {(selectedCantero || searchTerm) && (
              <button
                onClick={() => {
                  setSelectedCantero(null);
                  setSearchTerm('');
                }}
                className="btn btn-sm btn-outline mt-4"
              >
                Clear Filters
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
```

### Component: StorageLocationPreviewCard

Preview card component (detailed in 03_storage_location_preview.md).

```typescript
import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface Props {
  location: StorageLocationPreview;
  onClick: () => void;
}

export const StorageLocationPreviewCard: React.FC<Props> = ({ location, onClick }) => {
  const { preview } = location;

  if (!preview) {
    return (
      <div className="preview-card bg-white rounded-lg shadow p-4 cursor-pointer" onClick={onClick}>
        <h3 className="font-bold">{location.name}</h3>
        <p className="text-sm text-gray-500">{location.code}</p>
        <p className="text-xs text-gray-400 mt-2">No data available</p>
      </div>
    );
  }

  const getTrendIcon = () => {
    if (preview.quantity_change > 0) return <ArrowUp className="text-green-500 w-4 h-4" />;
    if (preview.quantity_change < 0) return <ArrowDown className="text-red-500 w-4 h-4" />;
    return <Minus className="text-gray-500 w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (preview.quantity_change > 0) return 'text-green-600';
    if (preview.quantity_change < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const getStatusBadge = () => {
    if (preview.error_message) {
      return <span className="badge badge-error badge-sm">Error</span>;
    }
    if (preview.status === 'completed') {
      return <span className="badge badge-success badge-sm">OK</span>;
    }
    return <span className="badge badge-warning badge-sm">Pending</span>;
  };

  return (
    <div
      className="preview-card bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer overflow-hidden"
      onClick={onClick}
    >
      {/* Image */}
      <div className="card-image relative">
        {preview.last_photo_thumbnail_url ? (
          <img
            src={preview.last_photo_thumbnail_url}
            alt={location.name}
            className="w-full h-48 object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-48 bg-gray-200 flex items-center justify-center">
            <span className="text-gray-400">No photo</span>
          </div>
        )}
        <div className="absolute top-2 left-2 right-2 flex justify-between">
          <span className="badge badge-primary badge-sm">{location.code}</span>
          {getStatusBadge()}
        </div>
      </div>

      {/* Content */}
      <div className="card-content p-4">
        <h3 className="font-bold text-lg truncate" title={location.name}>
          {location.name}
        </h3>
        <p className="text-xs text-gray-500">{location.cantero_name}</p>

        <div className="metrics grid grid-cols-2 gap-3 mt-3">
          {/* Quantity */}
          <div className="metric">
            <label className="text-xs text-gray-500">Quantity</label>
            <div className="flex items-center gap-1">
              <span className="text-xl font-bold">{preview.current_quantity}</span>
              {getTrendIcon()}
              <span className={`text-sm ${getTrendColor()}`}>
                {Math.abs(preview.quantity_change)}
              </span>
            </div>
          </div>

          {/* Maceta */}
          <div className="metric">
            <label className="text-xs text-gray-500">Maceta</label>
            <span className="text-lg font-bold">{preview.maceta_primary || 'N/A'}</span>
          </div>

          {/* Current Value */}
          <div className="metric">
            <label className="text-xs text-gray-500">Value</label>
            <span className="text-base font-semibold">
              ${preview.current_value.toFixed(0)}
            </span>
          </div>

          {/* Potential Value */}
          <div className="metric">
            <label className="text-xs text-gray-500">Potential</label>
            <span className="text-base font-semibold text-green-600">
              ${preview.potential_value.toFixed(0)}
            </span>
          </div>
        </div>

        {/* Category Breakdown */}
        {preview.category_counts && (
          <div className="category-breakdown mt-3 pt-3 border-t">
            <label className="text-xs text-gray-500">Categories</label>
            <div className="flex gap-2 mt-1 flex-wrap">
              {Object.entries(preview.category_counts).map(([category, count]) => (
                <span key={category} className="badge badge-outline badge-xs">
                  {category}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        {preview.last_photo_date && (
          <div className="footer mt-3 text-xs text-gray-500">
            Updated: {new Date(preview.last_photo_date).toLocaleDateString()}
          </div>
        )}
      </div>
    </div>
  );
};
```

## Performance Considerations

### No Additional API Calls

- **Data already loaded**: All storage areas and preview data fetched during bulk-load
- **Instant filtering**: Client-side cantero filtering (no network delay)
- **Fast navigation**: Click warehouse → immediate render (no loading)

### Lazy Rendering for Large Datasets

If warehouse has 500+ storage_locations, use virtualization:

```typescript
import { FixedSizeGrid as Grid } from 'react-window';

// Virtualized grid for performance
<Grid
  columnCount={4}
  columnWidth={300}
  height={window.innerHeight - 300}
  rowCount={Math.ceil(filteredLocations.length / 4)}
  rowHeight={350}
  width={window.innerWidth - 40}
>
  {({ columnIndex, rowIndex, style }) => {
    const index = rowIndex * 4 + columnIndex;
    const location = filteredLocations[index];
    if (!location) return null;
    return (
      <div style={style}>
        <StorageLocationPreviewCard
          location={location}
          onClick={() => handleLocationClick(location.id)}
        />
      </div>
    );
  }}
</Grid>
```

### Image Loading Optimization

- **Lazy loading**: Use `loading="lazy"` attribute
- **Presigned URLs**: S3 URLs generated during bulk-load (valid 1 hour)
- **Thumbnail size**: 300x300px JPEG (quality 80%) ~15-30KB each
- **Progressive rendering**: Cards appear as images load

## User Experience

### Navigation Flow

1. **User clicks warehouse** on map (Level 1)
2. **Internal view renders immediately** (no loading, data cached)
3. **Preview cards display** with thumbnails and metrics
4. **User filters by cantero** → Instant client-side filtering
5. **User clicks card** → Navigate to detail view (Level 3, fetches data)

### Loading States

- **Initial load**: Already done in Level 1 (bulk-load)
- **Filtering**: No loading (instant)
- **Sorting**: No loading (instant)
- **Images**: Lazy load with placeholder

### Error Handling

- **Missing warehouse**: Show "Not found" message with back button
- **No storage locations**: Show "No data" message
- **Failed images**: Show gray placeholder with "No photo" text

## Related Subflows

- **01_warehouse_map_overview.md**: Previous level - map with warehouses
- **03_storage_location_preview.md**: Preview card component details
- **04_storage_location_detail.md**: Next level - full detail view
- **05_historical_timeline.md**: Historical tracking for storage locations

## Version History

| Version | Date       | Changes                                      |
|---------|------------|----------------------------------------------|
| 1.0.0   | 2025-10-08 | Initial warehouse internal structure subflow |

---

**Notes:**

- Storage areas (canteros) organized by position: N, S, E, W, C
- Preview cards show key metrics without fetching additional data
- Client-side filtering provides instant responsiveness
- Virtualization recommended for warehouses with 500+ locations
- All data pre-loaded during bulk-load for optimal performance
