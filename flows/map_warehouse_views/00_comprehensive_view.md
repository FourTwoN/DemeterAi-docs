# Map Warehouse Views System - Comprehensive Overview

**Version:** 1.0.0
**Date:** 2025-10-08
**System:** DemeterAI Warehouse Navigation & Visualization

## Purpose

This diagram provides an **executive-level view** of the complete warehouse map navigation system, enabling users to visualize warehouses geographically, explore internal structures, view storage locations, and analyze historical data with progressive detail levels.

## Scope

- **Level**: High-level architectural overview
- **Audience**: Product managers, developers, UX designers, stakeholders
- **Detail**: End-to-end navigation from geographic map to storage location detail
- **Mermaid Version**: v11.3.0+ (using modern syntax)

## What It Represents

The diagram illustrates a **three-tier progressive detail system** for warehouse visualization and navigation:

### 1. Map Overview (Level 1) - Geographic View
**User goal:** See all warehouses on a map with summary metrics

- **PostGIS polygon rendering**: All warehouses displayed as colored polygons
- **Summary metrics per warehouse**:
  - Total errors count
  - Total claros (storage_locations) count
  - Total naves (storage_areas) count
- **Interactive map**: Click warehouse polygon → drill down to internal view
- **Technology**: React + Leaflet + PostGIS GeoJSON

### 2. Warehouse Internal Structure (Level 2) - Storage Areas View
**User goal:** Explore internal organization of selected warehouse

- **Storage areas (canteros)**: Display areas by position (Norte, Sur, Este, Oeste, Centro)
- **Storage locations grid**: All claros within selected warehouse
- **Preview cards** for each storage_location showing:
  - Quantity (total plants)
  - Maceta type (pot/container type)
  - Current value (monetary value)
  - Última foto (last photo timestamp)
  - Increase/decrease indicators (compared to previous photo)
  - Valor potencial (potential value based on growth)
- **Click action**: Click preview card → full detail view

### 3. Storage Location Detail (Level 3) - Full Detail View
**User goal:** See complete information about a specific storage_location

- **Processed image**: Latest photo with ML detections (bounding boxes)
- **Detection results**:
  - Total quantity by category (cactus, suculenta, injerto)
  - Empty containers count
  - Average confidence score
- **Financial data**:
  - Current price per unit
  - Total cost (quantity × price)
  - Potential value (estimated future value)
- **Container data**: Maceta types distribution
- **Quality metrics**: Quality score with optional graphs
- **Navigation options**: Configure location, view analytics

### 4. Historical Timeline (Level 4) - Evolution Over Time
**User goal:** Track storage_location changes over time

- **Photo periods**: Fotos taken every 3 months
- **Per period metrics**:
  - Fecha (date)
  - Cantidad inicial (starting quantity)
  - Muertes (deaths/losses)
  - Transplantes (transplants out)
  - Plantados (new plantings)
  - Cantidad vendida (quantity sold)
  - Cantidad final (ending quantity)
- **Full traceability**: Complete audit trail
- **Visual timeline**: Graph showing quantity evolution

## Key Components

### Level 1: Map Overview Features

**Geographic Visualization:**
- PostGIS polygons for each warehouse (stored as geometry type)
- Color coding by warehouse type (greenhouse, shadehouse, open_field, tunnel)
- Hover tooltip showing warehouse name and summary stats
- Zoom/pan controls for large facilities

**Summary Metrics:**
- **Errors count**: Total processing errors or warnings
- **Claros count**: Total storage_locations in warehouse
- **Naves count**: Total storage_areas in warehouse
- **Active status**: Visual indicator for active/inactive warehouses

**Performance Optimization:**
- **Bulk load on app init**: Load all warehouse + internal structure data at once
- **Materialized views**: Pre-aggregated metrics for fast rendering
- **GeoJSON caching**: Cache polygon coordinates (rarely change)
- **Single API call**: `/api/v1/map/bulk-load` returns everything for levels 1-2

### Level 2: Warehouse Internal Structure Features

**Storage Areas Display:**
- Grid or map layout showing canteros (N, S, E, O, C)
- Color coding by utilization rate
- Click area to filter storage_locations

**Storage Location Preview Cards:**
- **Thumbnail**: Small image from última foto
- **Quantity badge**: Current plant count with trend arrow (↑↓)
- **Maceta icon**: Visual indicator of container type
- **Value display**: Current monetary value
- **Last updated**: Timestamp of última foto
- **Status indicator**: Color badge (green=healthy, yellow=warning, red=error)

**Filtering & Search:**
- Filter by storage_area (cantero)
- Search by storage_location code/name
- Sort by: quantity, value, last_updated, errors

**Performance Optimization:**
- **Already loaded**: Data fetched during initial bulk load
- **Lazy rendering**: Render preview cards as user scrolls (virtualization)
- **Thumbnail URLs**: Presigned S3 URLs from bulk load response
- **No additional API calls**: Everything cached from initial load

### Level 3: Storage Location Detail Features

**Image Display:**
- Full-size processed image with ML detections
- Bounding boxes color-coded by category
- Zoom/pan controls
- Toggle annotations on/off

**Detection Breakdown:**
- **By category**: Cactus count, Suculenta count, Injerto count
- **Empty containers**: Count of empty pots
- **Confidence scores**: Average and distribution
- **Manual adjustments**: User can add/remove detections

**Financial Information:**
- Current price per unit (from product catalog)
- Total cost calculation (quantity × price)
- Potential value (based on growth stage and market trends)
- ROI indicators

**Container Distribution:**
- Pie chart or bar chart showing maceta types
- Count per maceta size (8cm, 10cm, 12cm, etc.)

**Quality Metrics:**
- Overall quality score (0-100)
- Optional graphs: quality trend over time
- Health indicators (growth rate, mortality rate)

**Action Buttons:**
- **Configure**: Edit storage_location settings
- **View Analytics**: Navigate to analytics dashboard
- **View History**: Open historical timeline
- **Take Photo**: Trigger new photo capture

**Performance Optimization:**
- **Fetch on demand**: Only load detail data when user clicks preview card
- **Separate API call**: `/api/v1/storage-locations/{id}/detail`
- **Response time target**: < 300ms
- **Image lazy load**: Load full image only when detail view opens
- **Cache detections**: Store detection results in Redis (TTL: 1 hour)

### Level 4: Historical Timeline Features

**Timeline View:**
- Horizontal timeline showing all photo periods
- Each period represented as a card or timeline node
- Click period to expand details

**Period Details:**
- **Fecha**: Start and end date of period
- **Foto**: Thumbnail of photo from that period
- **Cantidad inicial**: Starting quantity (from previous period's end)
- **Muertes**: Plants that died during period
- **Transplantes**: Plants moved out to other locations
- **Plantados**: New plants added during period
- **Cantidad vendida**: Plants sold during period
- **Cantidad final**: Ending quantity (should match next period's start)

**Visualizations:**
- Line chart showing quantity over time
- Stacked bar chart showing movements by type
- Cumulative mortality rate
- Growth rate trend

**Traceability:**
- Link each movement to source transaction (stock_movements table)
- Show user who made each change
- Audit trail for compliance

**Performance Optimization:**
- **Separate API call**: `/api/v1/storage-locations/{id}/history`
- **Fetch on demand**: Only load when user clicks "View History"
- **Response time target**: < 500ms
- **Pagination**: Load 12 periods at a time (3 years of quarterly data)
- **Materialized view**: Pre-aggregate period data for fast queries

## Database Schema

### Core Tables

#### warehouses
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

CREATE INDEX idx_warehouses_geojson ON warehouses USING GIST (geojson_coordinates);
CREATE INDEX idx_warehouses_centroid ON warehouses USING GIST (centroid);
CREATE INDEX idx_warehouses_active ON warehouses(active);
```

#### storage_areas
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

CREATE INDEX idx_storage_areas_warehouse ON storage_areas(warehouse_id);
CREATE INDEX idx_storage_areas_geojson ON storage_areas USING GIST (geojson_coordinates);
CREATE INDEX idx_storage_areas_position ON storage_areas(warehouse_id, position);
```

#### storage_locations
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

CREATE INDEX idx_storage_locations_area ON storage_locations(storage_area_id);
CREATE INDEX idx_storage_locations_geojson ON storage_locations USING GIST (geojson_coordinates);
CREATE INDEX idx_storage_locations_active ON storage_locations(active);
CREATE INDEX idx_storage_locations_qr ON storage_locations(qr_code);
```

#### photo_processing_sessions
```sql
CREATE TABLE photo_processing_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL,
    storage_location_id INTEGER REFERENCES storage_locations(id),
    original_image_id INTEGER NOT NULL REFERENCES s3_images(id),
    processed_image_id INTEGER REFERENCES s3_images(id),
    total_detected INTEGER,
    total_estimated INTEGER,
    total_empty_containers INTEGER,
    avg_confidence NUMERIC(5,4),
    category_counts JSONB,  -- {"cactus": 50, "suculenta": 40, "injerto": 30}
    status VARCHAR(50) DEFAULT 'pending',  -- pending|processing|completed|failed
    error_message TEXT,
    validated BOOLEAN DEFAULT false,
    validated_by_user_id INTEGER REFERENCES users(id),
    validation_date TIMESTAMP,
    manual_adjustments JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_storage_location ON photo_processing_sessions(storage_location_id);
CREATE INDEX idx_sessions_created_at ON photo_processing_sessions(storage_location_id, created_at DESC);
CREATE INDEX idx_sessions_status ON photo_processing_sessions(status);
```

#### stock_batches
```sql
CREATE TABLE stock_batches (
    id SERIAL PRIMARY KEY,
    current_storage_bin_id INTEGER REFERENCES storage_locations(id),  -- current location
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_state_id INTEGER REFERENCES product_states(id),
    packaging_catalog_id INTEGER REFERENCES packaging_catalog(id),  -- maceta type
    quantity_current INTEGER NOT NULL,
    quality_score NUMERIC(5,2),  -- 0.00 to 100.00
    cost_per_unit NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_stock_batches_location ON stock_batches(current_storage_bin_id);
CREATE INDEX idx_stock_batches_product ON stock_batches(product_id);
CREATE INDEX idx_stock_batches_quality ON stock_batches(quality_score DESC);
```

#### stock_movements
```sql
CREATE TABLE stock_movements (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES stock_batches(id),
    movement_type VARCHAR(50) NOT NULL,  -- plantar|sembrar|transplante|muerte|ventas|foto|ajuste
    quantity INTEGER NOT NULL,
    from_location_id INTEGER REFERENCES storage_locations(id),
    to_location_id INTEGER REFERENCES storage_locations(id),
    reference_session_id UUID REFERENCES photo_processing_sessions(session_id),  -- links to photo
    notes TEXT,
    created_by_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT chk_movement_type CHECK (movement_type IN ('plantar', 'sembrar', 'transplante', 'muerte', 'ventas', 'foto', 'ajuste'))
);

CREATE INDEX idx_stock_movements_batch ON stock_movements(batch_id);
CREATE INDEX idx_stock_movements_type ON stock_movements(movement_type);
CREATE INDEX idx_stock_movements_created_at ON stock_movements(created_at DESC);
CREATE INDEX idx_stock_movements_location_from ON stock_movements(from_location_id);
CREATE INDEX idx_stock_movements_location_to ON stock_movements(to_location_id);
```

### Materialized Views for Performance

#### mv_warehouse_summary
Pre-aggregated warehouse metrics for map overview.

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
    COUNT(DISTINCT CASE
        WHEN pps.status = 'failed' OR pps.error_message IS NOT NULL
        THEN pps.id
    END) AS errors_count,
    SUM(COALESCE(pps.total_detected, 0)) AS total_plants,
    MAX(pps.created_at) AS last_photo_date
FROM warehouses w
LEFT JOIN storage_areas sa ON sa.warehouse_id = w.id
LEFT JOIN storage_locations sl ON sl.storage_area_id = sa.id
LEFT JOIN photo_processing_sessions pps ON pps.storage_location_id = sl.id
WHERE w.active = true
GROUP BY w.id, w.code, w.name, w.type, w.geojson_coordinates, w.centroid, w.area_m2, w.active;

CREATE UNIQUE INDEX idx_mv_warehouse_summary_id ON mv_warehouse_summary(warehouse_id);
CREATE INDEX idx_mv_warehouse_summary_geojson ON mv_warehouse_summary USING GIST (geojson_coordinates);
```

**Refresh strategy:** Refresh every 5 minutes via cron job or on-demand after major updates.

```sql
-- Refresh command
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_warehouse_summary;
```

#### mv_storage_location_preview
Pre-aggregated storage_location data for preview cards.

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
        processed_image_id
    FROM photo_processing_sessions
    WHERE status = 'completed' AND storage_location_id IS NOT NULL
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
        JSONB_OBJECT_AGG(COALESCE(pc.name, 'unknown'), batch_counts.count) AS maceta_distribution
    FROM stock_batches sb
    LEFT JOIN packaging_catalog pc ON pc.id = sb.packaging_catalog_id
    LEFT JOIN (
        SELECT current_storage_bin_id, packaging_catalog_id, COUNT(*) AS count
        FROM stock_batches
        GROUP BY current_storage_bin_id, packaging_catalog_id
    ) batch_counts ON batch_counts.current_storage_bin_id = sb.current_storage_bin_id
        AND batch_counts.packaging_catalog_id = sb.packaging_catalog_id
    GROUP BY current_storage_bin_id
)
SELECT
    sl.id AS storage_location_id,
    sl.code AS storage_location_code,
    sl.name AS storage_location_name,
    sl.storage_area_id,
    sa.warehouse_id,
    sa.position AS cantero_position,
    ls.session_id AS last_session_id,
    ls.last_photo_date,
    ls.processed_image_id,
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

CREATE UNIQUE INDEX idx_mv_location_preview_id ON mv_storage_location_preview(storage_location_id);
CREATE INDEX idx_mv_location_preview_warehouse ON mv_storage_location_preview(warehouse_id);
CREATE INDEX idx_mv_location_preview_area ON mv_storage_location_preview(storage_area_id);
CREATE INDEX idx_mv_location_preview_date ON mv_storage_location_preview(last_photo_date DESC NULLS LAST);
```

**Refresh strategy:** Refresh every 10 minutes or after photo processing completes.

#### mv_storage_location_history
Pre-aggregated historical timeline data.

```sql
CREATE MATERIALIZED VIEW mv_storage_location_history AS
WITH period_boundaries AS (
    SELECT
        storage_location_id,
        created_at AS period_start,
        LEAD(created_at) OVER (PARTITION BY storage_location_id ORDER BY created_at) AS period_end,
        session_id,
        total_detected AS quantity_final
    FROM photo_processing_sessions
    WHERE status = 'completed' AND storage_location_id IS NOT NULL
),
period_movements AS (
    SELECT
        pb.storage_location_id,
        pb.period_start,
        pb.period_end,
        pb.session_id,
        pb.quantity_final,
        LAG(pb.quantity_final) OVER (PARTITION BY pb.storage_location_id ORDER BY pb.period_start) AS quantity_inicial,
        COALESCE(SUM(CASE WHEN sm.movement_type = 'muerte' THEN sm.quantity ELSE 0 END), 0) AS muertes,
        COALESCE(SUM(CASE WHEN sm.movement_type = 'transplante' AND sm.from_location_id = pb.storage_location_id THEN sm.quantity ELSE 0 END), 0) AS transplantes,
        COALESCE(SUM(CASE WHEN sm.movement_type IN ('plantar', 'sembrar') THEN sm.quantity ELSE 0 END), 0) AS plantados,
        COALESCE(SUM(CASE WHEN sm.movement_type = 'ventas' THEN sm.quantity ELSE 0 END), 0) AS vendidos
    FROM period_boundaries pb
    LEFT JOIN stock_movements sm ON (sm.from_location_id = pb.storage_location_id OR sm.to_location_id = pb.storage_location_id)
        AND sm.created_at >= pb.period_start
        AND (pb.period_end IS NULL OR sm.created_at < pb.period_end)
    GROUP BY pb.storage_location_id, pb.period_start, pb.period_end, pb.session_id, pb.quantity_final
)
SELECT
    storage_location_id,
    period_start AS fecha,
    period_end,
    session_id,
    quantity_inicial,
    muertes,
    transplantes,
    plantados,
    vendidos,
    quantity_final AS cantidad_final,
    quantity_final - COALESCE(quantity_inicial, 0) AS net_change
FROM period_movements
ORDER BY storage_location_id, period_start;

CREATE INDEX idx_mv_location_history_location ON mv_storage_location_history(storage_location_id);
CREATE INDEX idx_mv_location_history_fecha ON mv_storage_location_history(fecha DESC);
```

**Refresh strategy:** Refresh daily at midnight or on-demand after significant stock movements.

## API Endpoints

### Level 1: Map Overview

#### GET /api/v1/map/bulk-load
Bulk load all warehouse and storage_location data for initial app load.

**Request:**
```http
GET /api/v1/map/bulk-load HTTP/1.1
Authorization: Bearer <token>
```

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
        "coordinates": [[[-58.381, -34.603], [-58.380, -34.603], [-58.380, -34.604], [-58.381, -34.604], [-58.381, -34.603]]]
      },
      "centroid": {"type": "Point", "coordinates": [-58.3805, -34.6035]},
      "area_m2": 1200.50,
      "metrics": {
        "naves_count": 5,
        "claros_count": 120,
        "errors_count": 3,
        "total_plants": 14500,
        "last_photo_date": "2025-10-08T10:30:00Z"
      }
    }
  ],
  "storage_areas": [
    {
      "id": 1,
      "warehouse_id": 1,
      "code": "WH-001-N",
      "name": "Norte",
      "position": "N",
      "geojson": {"type": "Polygon", "coordinates": [...]},
      "area_m2": 250.00
    }
  ],
  "storage_locations": [
    {
      "id": 1,
      "storage_area_id": 1,
      "warehouse_id": 1,
      "code": "WH-001-N-001",
      "name": "Rack 1 Shelf 1",
      "cantero_position": "N",
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
        "category_counts": {"cactus": 50, "suculenta": 40, "injerto": 30}
      }
    }
  ],
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
- Response time: < 1000ms (bulk data)
- Payload size: ~500KB - 2MB (compressed)
- Cache: Redis cache for 10 minutes (materialized views refreshed every 10 min)
- Compression: GZIP enabled

**Notes:**
- Single API call loads everything for levels 1 and 2
- Frontend caches this data locally (IndexedDB or state management)
- Only refresh when user manually triggers or after 10 minutes
- Thumbnail URLs are presigned S3 URLs (valid for 1 hour)

### Level 2: Warehouse Internal Structure

**No additional API call needed** - data already loaded from `/api/v1/map/bulk-load`

Frontend filters and displays data from cached bulk load response.

### Level 3: Storage Location Detail

#### GET /api/v1/storage-locations/{id}/detail
Fetch detailed information for a specific storage_location.

**Request:**
```http
GET /api/v1/storage-locations/1/detail HTTP/1.1
Authorization: Bearer <token>
```

**Response:**
```json
{
  "storage_location": {
    "id": 1,
    "code": "WH-001-N-001",
    "name": "Rack 1 Shelf 1",
    "description": "North section, first rack",
    "storage_area": {
      "id": 1,
      "code": "WH-001-N",
      "name": "Norte",
      "position": "N"
    },
    "warehouse": {
      "id": 1,
      "code": "WH-001",
      "name": "Warehouse A"
    },
    "active": true
  },
  "latest_session": {
    "session_id": "uuid-1",
    "processed_image_url": "https://s3.../annotated/uuid-1.jpg",
    "original_image_url": "https://s3.../originals/uuid-1.jpg",
    "created_at": "2025-10-08T10:30:00Z",
    "total_detected": 120,
    "total_estimated": 125,
    "total_empty_containers": 5,
    "avg_confidence": 0.92,
    "category_counts": {
      "cactus": 50,
      "suculenta": 40,
      "injerto": 30
    },
    "validated": true,
    "validated_by": "john.doe@demeter.com",
    "validation_date": "2025-10-08T11:00:00Z"
  },
  "detections": [
    {
      "id": 1,
      "category": "cactus",
      "bbox": {"x": 120, "y": 80, "width": 50, "height": 60},
      "confidence": 0.95,
      "product_id": 42,
      "product_name": "Echeveria elegans"
    }
  ],
  "stock_summary": {
    "total_quantity": 120,
    "total_value": 1200.00,
    "potential_value": 1560.00,
    "avg_quality_score": 85.5,
    "maceta_distribution": {
      "8cm": 30,
      "10cm": 70,
      "12cm": 20
    },
    "cost_per_unit_avg": 10.00
  },
  "financial": {
    "current_price_per_unit": 10.00,
    "total_cost": 1200.00,
    "potential_revenue": 1560.00,
    "roi_percent": 30.0
  },
  "quality_metrics": {
    "overall_score": 85.5,
    "health_score": 90.0,
    "growth_rate_percent": 5.2,
    "mortality_rate_percent": 1.5
  }
}
```

**Performance:**
- Response time: < 300ms
- Cache: Redis cache for 1 hour (invalidated on new photo)
- Fetch on demand: Only load when user clicks preview card

### Level 4: Historical Timeline

#### GET /api/v1/storage-locations/{id}/history
Fetch historical timeline for a storage_location.

**Request:**
```http
GET /api/v1/storage-locations/1/history?page=1&per_page=12 HTTP/1.1
Authorization: Bearer <token>
```

**Response:**
```json
{
  "storage_location": {
    "id": 1,
    "code": "WH-001-N-001",
    "name": "Rack 1 Shelf 1"
  },
  "periods": [
    {
      "fecha": "2025-10-08T00:00:00Z",
      "period_end": null,
      "session_id": "uuid-1",
      "photo_thumbnail_url": "https://s3.../thumbnails/uuid-1.jpg",
      "cantidad_inicial": 115,
      "muertes": 5,
      "transplantes": 10,
      "plantados": 20,
      "cantidad_vendida": 0,
      "cantidad_final": 120,
      "net_change": 5
    },
    {
      "fecha": "2025-07-08T00:00:00Z",
      "period_end": "2025-10-08T00:00:00Z",
      "session_id": "uuid-old-1",
      "photo_thumbnail_url": "https://s3.../thumbnails/uuid-old-1.jpg",
      "cantidad_inicial": 100,
      "muertes": 3,
      "transplantes": 5,
      "plantados": 23,
      "cantidad_vendida": 0,
      "cantidad_final": 115,
      "net_change": 15
    }
  ],
  "summary": {
    "total_periods": 8,
    "earliest_date": "2023-10-08T00:00:00Z",
    "latest_date": "2025-10-08T00:00:00Z",
    "total_muertes": 45,
    "total_transplantes": 80,
    "total_plantados": 200,
    "total_vendidos": 75,
    "overall_growth_rate_percent": 15.5
  },
  "pagination": {
    "page": 1,
    "per_page": 12,
    "total_pages": 1,
    "total_items": 8
  }
}
```

**Performance:**
- Response time: < 500ms
- Cache: Redis cache for 1 day (materialized view refreshed daily)
- Pagination: 12 periods per page (3 years of quarterly data)
- Fetch on demand: Only load when user clicks "View History"

## PostGIS Queries

### Query 1: Get All Warehouses as GeoJSON
```sql
SELECT
    id,
    code,
    name,
    type,
    ST_AsGeoJSON(geojson_coordinates)::json AS geojson,
    ST_AsGeoJSON(centroid)::json AS centroid,
    area_m2,
    active
FROM warehouses
WHERE active = true;
```

### Query 2: Get Warehouses Within Bounds (Map Viewport)
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
    ws.errors_count,
    ws.total_plants,
    ws.last_photo_date
FROM mv_warehouse_summary ws
WHERE ST_Intersects(
    ws.geojson_coordinates,
    ST_MakeEnvelope($1, $2, $3, $4, 4326)  -- minLon, minLat, maxLon, maxLat
)
AND ws.active = true;
```

### Query 3: Find Storage Location by GPS Coordinates
```sql
SELECT
    sl.id,
    sl.code,
    sl.name,
    sa.name AS storage_area_name,
    w.name AS warehouse_name,
    ST_Distance(
        sl.centroid,
        ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
    ) AS distance_meters
FROM storage_locations sl
INNER JOIN storage_areas sa ON sa.id = sl.storage_area_id
INNER JOIN warehouses w ON w.id = sa.warehouse_id
WHERE ST_DWithin(
    sl.centroid::geography,
    ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
    10  -- 10 meters radius
)
AND sl.active = true
ORDER BY distance_meters ASC
LIMIT 1;
```

## Frontend Components (React + Leaflet)

### Component 1: MapOverview
Main map component displaying all warehouses.

```typescript
import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polygon, Popup, useMap } from 'react-leaflet';
import { LatLngBounds } from 'leaflet';

interface WarehouseSummary {
  id: number;
  code: string;
  name: string;
  type: string;
  geojson: GeoJSON.Polygon;
  centroid: GeoJSON.Point;
  metrics: {
    naves_count: number;
    claros_count: number;
    errors_count: number;
    total_plants: number;
  };
}

export const MapOverview: React.FC = () => {
  const [warehouses, setWarehouses] = useState<WarehouseSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Bulk load all data on mount
    fetch('/api/v1/map/bulk-load')
      .then(res => res.json())
      .then(data => {
        setWarehouses(data.warehouses);
        // Store storage_locations in global state for later use
        globalState.setStorageLocations(data.storage_locations);
        setLoading(false);
      });
  }, []);

  const getWarehouseColor = (type: string) => {
    switch (type) {
      case 'greenhouse': return '#4CAF50';
      case 'shadehouse': return '#2196F3';
      case 'open_field': return '#FFC107';
      case 'tunnel': return '#9C27B0';
      default: return '#757575';
    }
  };

  if (loading) return <div>Loading map...</div>;

  return (
    <MapContainer
      center={[-34.603722, -58.381592]}
      zoom={15}
      style={{ height: '100vh', width: '100%' }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />

      {warehouses.map(warehouse => (
        <Polygon
          key={warehouse.id}
          positions={warehouse.geojson.coordinates[0].map(coord => [coord[1], coord[0]])}
          pathOptions={{
            color: getWarehouseColor(warehouse.type),
            fillColor: getWarehouseColor(warehouse.type),
            fillOpacity: 0.3,
            weight: 2
          }}
          eventHandlers={{
            click: () => {
              // Navigate to warehouse internal view
              window.location.href = `/warehouses/${warehouse.id}/internal`;
            }
          }}
        >
          <Popup>
            <div>
              <h3>{warehouse.name}</h3>
              <p>Type: {warehouse.type}</p>
              <p>Naves: {warehouse.metrics.naves_count}</p>
              <p>Claros: {warehouse.metrics.claros_count}</p>
              <p>Errors: {warehouse.metrics.errors_count}</p>
              <p>Total Plants: {warehouse.metrics.total_plants}</p>
              <button onClick={() => window.location.href = `/warehouses/${warehouse.id}/internal`}>
                View Details
              </button>
            </div>
          </Popup>
        </Polygon>
      ))}
    </MapContainer>
  );
};
```

### Component 2: WarehouseInternalView
Display storage areas and storage locations with preview cards.

```typescript
import React, { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { StorageLocationPreviewCard } from './StorageLocationPreviewCard';

interface StorageLocationPreview {
  id: number;
  code: string;
  name: string;
  cantero_position: 'N' | 'S' | 'E' | 'W' | 'C';
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
    category_counts: Record<string, number>;
  };
}

export const WarehouseInternalView: React.FC = () => {
  const { warehouseId } = useParams<{ warehouseId: string }>();
  const [selectedCantero, setSelectedCantero] = useState<string | null>(null);

  // Get data from global state (already loaded in MapOverview)
  const storageLocations = useMemo(() => {
    return globalState.storageLocations.filter(
      loc => loc.warehouse_id === parseInt(warehouseId)
    );
  }, [warehouseId]);

  const filteredLocations = useMemo(() => {
    if (!selectedCantero) return storageLocations;
    return storageLocations.filter(loc => loc.cantero_position === selectedCantero);
  }, [storageLocations, selectedCantero]);

  const canteroOptions = ['N', 'S', 'E', 'W', 'C'];

  return (
    <div className="warehouse-internal-view">
      <header>
        <h1>Warehouse Internal Structure</h1>
        <div className="cantero-filter">
          <button
            className={!selectedCantero ? 'active' : ''}
            onClick={() => setSelectedCantero(null)}
          >
            All
          </button>
          {canteroOptions.map(cantero => (
            <button
              key={cantero}
              className={selectedCantero === cantero ? 'active' : ''}
              onClick={() => setSelectedCantero(cantero)}
            >
              {cantero === 'N' ? 'Norte' : cantero === 'S' ? 'Sur' : cantero === 'E' ? 'Este' : cantero === 'W' ? 'Oeste' : 'Centro'}
            </button>
          ))}
        </div>
      </header>

      <div className="storage-locations-grid">
        {filteredLocations.map(location => (
          <StorageLocationPreviewCard
            key={location.id}
            location={location}
            onClick={() => {
              // Navigate to storage location detail
              window.location.href = `/storage-locations/${location.id}/detail`;
            }}
          />
        ))}
      </div>
    </div>
  );
};
```

### Component 3: StorageLocationPreviewCard
Preview card component for storage_location.

```typescript
import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface Props {
  location: StorageLocationPreview;
  onClick: () => void;
}

export const StorageLocationPreviewCard: React.FC<Props> = ({ location, onClick }) => {
  const { preview } = location;

  const getTrendIcon = () => {
    if (preview.quantity_change > 0) return <ArrowUp className="text-green-500" />;
    if (preview.quantity_change < 0) return <ArrowDown className="text-red-500" />;
    return <Minus className="text-gray-500" />;
  };

  const getTrendColor = () => {
    if (preview.quantity_change > 0) return 'text-green-600';
    if (preview.quantity_change < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <div
      className="preview-card cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onClick}
    >
      <div className="card-image">
        <img
          src={preview.last_photo_thumbnail_url}
          alt={location.name}
          className="w-full h-48 object-cover"
        />
        <div className="image-overlay">
          <span className="badge">{location.code}</span>
        </div>
      </div>

      <div className="card-content p-4">
        <h3 className="font-bold text-lg">{location.name}</h3>

        <div className="metrics grid grid-cols-2 gap-2 mt-2">
          <div className="metric">
            <label className="text-sm text-gray-500">Quantity</label>
            <div className="flex items-center gap-1">
              <span className="text-xl font-bold">{preview.current_quantity}</span>
              {getTrendIcon()}
              <span className={`text-sm ${getTrendColor()}`}>
                {Math.abs(preview.quantity_change)}
              </span>
            </div>
          </div>

          <div className="metric">
            <label className="text-sm text-gray-500">Maceta</label>
            <span className="text-xl font-bold">{preview.maceta_primary}</span>
          </div>

          <div className="metric">
            <label className="text-sm text-gray-500">Current Value</label>
            <span className="text-lg font-semibold">
              ${preview.current_value.toFixed(2)}
            </span>
          </div>

          <div className="metric">
            <label className="text-sm text-gray-500">Potential Value</label>
            <span className="text-lg font-semibold text-green-600">
              ${preview.potential_value.toFixed(2)}
            </span>
          </div>
        </div>

        <div className="category-breakdown mt-2">
          <label className="text-sm text-gray-500">Categories</label>
          <div className="flex gap-2 text-xs">
            {Object.entries(preview.category_counts).map(([category, count]) => (
              <span key={category} className="badge badge-sm">
                {category}: {count}
              </span>
            ))}
          </div>
        </div>

        <div className="footer mt-2 text-xs text-gray-500">
          Last updated: {new Date(preview.last_photo_date).toLocaleDateString()}
        </div>
      </div>
    </div>
  );
};
```

### Component 4: StorageLocationDetail
Full detail view for storage_location.

```typescript
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

interface StorageLocationDetail {
  storage_location: {
    id: number;
    code: string;
    name: string;
    // ... other fields
  };
  latest_session: {
    session_id: string;
    processed_image_url: string;
    total_detected: number;
    category_counts: Record<string, number>;
    // ... other fields
  };
  stock_summary: {
    total_quantity: number;
    total_value: number;
    potential_value: number;
    maceta_distribution: Record<string, number>;
    // ... other fields
  };
  // ... other sections
}

export const StorageLocationDetail: React.FC = () => {
  const { locationId } = useParams<{ locationId: string }>();
  const [detail, setDetail] = useState<StorageLocationDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch detail data on mount (on-demand)
    fetch(`/api/v1/storage-locations/${locationId}/detail`)
      .then(res => res.json())
      .then(data => {
        setDetail(data);
        setLoading(false);
      });
  }, [locationId]);

  if (loading) return <div>Loading...</div>;
  if (!detail) return <div>Not found</div>;

  return (
    <div className="storage-location-detail">
      <header>
        <h1>{detail.storage_location.name}</h1>
        <p className="text-gray-500">{detail.storage_location.code}</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column: Image */}
        <div className="image-section">
          <img
            src={detail.latest_session.processed_image_url}
            alt="Processed"
            className="w-full rounded-lg shadow-lg"
          />
        </div>

        {/* Right column: Details */}
        <div className="details-section">
          <section className="detections mb-6">
            <h2 className="text-xl font-bold mb-2">Detection Results</h2>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(detail.latest_session.category_counts).map(([category, count]) => (
                <div key={category} className="stat-card">
                  <label className="text-sm text-gray-500">{category}</label>
                  <span className="text-2xl font-bold">{count}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="financial mb-6">
            <h2 className="text-xl font-bold mb-2">Financial Information</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="stat-card">
                <label className="text-sm text-gray-500">Current Value</label>
                <span className="text-2xl font-bold">
                  ${detail.stock_summary.total_value.toFixed(2)}
                </span>
              </div>
              <div className="stat-card">
                <label className="text-sm text-gray-500">Potential Value</label>
                <span className="text-2xl font-bold text-green-600">
                  ${detail.stock_summary.potential_value.toFixed(2)}
                </span>
              </div>
            </div>
          </section>

          <section className="macetas mb-6">
            <h2 className="text-xl font-bold mb-2">Container Distribution</h2>
            <div className="flex gap-2">
              {Object.entries(detail.stock_summary.maceta_distribution).map(([size, count]) => (
                <div key={size} className="badge badge-lg">
                  {size}: {count}
                </div>
              ))}
            </div>
          </section>

          <section className="actions">
            <button
              className="btn btn-primary"
              onClick={() => window.location.href = `/storage-locations/${locationId}/history`}
            >
              View History
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => window.location.href = `/storage-locations/${locationId}/configure`}
            >
              Configure
            </button>
          </section>
        </div>
      </div>
    </div>
  );
};
```

### Component 5: HistoricalTimeline
Historical timeline component.

```typescript
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface Period {
  fecha: string;
  session_id: string;
  photo_thumbnail_url: string;
  cantidad_inicial: number;
  muertes: number;
  transplantes: number;
  plantados: number;
  cantidad_vendida: number;
  cantidad_final: number;
  net_change: number;
}

export const HistoricalTimeline: React.FC = () => {
  const { locationId } = useParams<{ locationId: string }>();
  const [periods, setPeriods] = useState<Period[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch history data on mount (on-demand)
    fetch(`/api/v1/storage-locations/${locationId}/history`)
      .then(res => res.json())
      .then(data => {
        setPeriods(data.periods);
        setLoading(false);
      });
  }, [locationId]);

  if (loading) return <div>Loading history...</div>;

  const chartData = periods.map(period => ({
    date: new Date(period.fecha).toLocaleDateString(),
    quantity: period.cantidad_final,
    muertes: period.muertes,
    plantados: period.plantados,
    vendidos: period.cantidad_vendida
  }));

  return (
    <div className="historical-timeline">
      <header>
        <h1>Historical Timeline</h1>
      </header>

      <section className="chart-section mb-8">
        <h2 className="text-xl font-bold mb-4">Quantity Evolution</h2>
        <LineChart width={800} height={400} data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="quantity" stroke="#8884d8" name="Total Quantity" />
        </LineChart>
      </section>

      <section className="periods-list">
        <h2 className="text-xl font-bold mb-4">Period Details</h2>
        <div className="grid grid-cols-1 gap-4">
          {periods.map(period => (
            <div key={period.session_id} className="period-card border rounded-lg p-4">
              <div className="flex gap-4">
                <img
                  src={period.photo_thumbnail_url}
                  alt="Period"
                  className="w-24 h-24 object-cover rounded"
                />
                <div className="flex-1">
                  <h3 className="font-bold text-lg">
                    {new Date(period.fecha).toLocaleDateString()}
                  </h3>
                  <div className="grid grid-cols-3 gap-2 mt-2 text-sm">
                    <div>
                      <label className="text-gray-500">Inicial:</label>
                      <span className="font-semibold ml-1">{period.cantidad_inicial}</span>
                    </div>
                    <div>
                      <label className="text-gray-500">Muertes:</label>
                      <span className="font-semibold ml-1 text-red-600">-{period.muertes}</span>
                    </div>
                    <div>
                      <label className="text-gray-500">Transplantes:</label>
                      <span className="font-semibold ml-1 text-orange-600">-{period.transplantes}</span>
                    </div>
                    <div>
                      <label className="text-gray-500">Plantados:</label>
                      <span className="font-semibold ml-1 text-green-600">+{period.plantados}</span>
                    </div>
                    <div>
                      <label className="text-gray-500">Vendidos:</label>
                      <span className="font-semibold ml-1 text-blue-600">-{period.cantidad_vendida}</span>
                    </div>
                    <div>
                      <label className="text-gray-500">Final:</label>
                      <span className="font-semibold ml-1">{period.cantidad_final}</span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <span className={`badge ${period.net_change >= 0 ? 'badge-success' : 'badge-error'}`}>
                      Net Change: {period.net_change > 0 ? '+' : ''}{period.net_change}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
```

## Performance Optimization Strategy

### Initial Load (Levels 1-2)
**Strategy: Bulk Load Everything**

1. **Single API call** on app init: `/api/v1/map/bulk-load`
2. **Returns:**
   - All warehouses with summary metrics
   - All storage_areas
   - All storage_locations with preview data
3. **Frontend caching:**
   - Store in global state (Redux, Zustand, Context)
   - Or IndexedDB for persistence
4. **Refresh strategy:**
   - Manual refresh button
   - Auto-refresh every 10 minutes (materialized view refresh interval)
5. **Benefits:**
   - Fast navigation between map and warehouse views (no loading)
   - Smooth user experience
   - Reduced server load (fewer requests)

### Detail View (Level 3)
**Strategy: Fetch On-Demand**

1. **Separate API call** when user clicks preview card: `/api/v1/storage-locations/{id}/detail`
2. **Returns:**
   - Full detection results
   - Processed image URLs
   - Financial data
   - Quality metrics
3. **Why not bulk load:**
   - Detail data is large (detections, images)
   - User won't view all locations
   - Would slow down initial load
4. **Caching:**
   - Redis cache for 1 hour
   - Frontend cache for session duration
5. **Benefits:**
   - Fast initial load
   - Only fetch what's needed
   - Better bandwidth usage

### History View (Level 4)
**Strategy: Fetch On-Demand**

1. **Separate API call** when user clicks "View History": `/api/v1/storage-locations/{id}/history`
2. **Returns:**
   - Historical periods (paginated)
   - Period thumbnails
   - Movement aggregates
3. **Why not bulk load:**
   - History is rarely viewed
   - Data is large (many periods)
   - Not needed for main workflows
4. **Caching:**
   - Redis cache for 1 day
   - Materialized view refreshed daily
5. **Benefits:**
   - Minimal initial load time
   - History available when needed
   - Reduced memory footprint

### Database Optimization

#### Materialized Views
- **mv_warehouse_summary**: Refresh every 5 minutes
- **mv_storage_location_preview**: Refresh every 10 minutes
- **mv_storage_location_history**: Refresh daily at midnight

**Refresh commands:**
```sql
-- Scheduled via cron job or pg_cron extension
SELECT cron.schedule('refresh-warehouse-summary', '*/5 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_warehouse_summary');
SELECT cron.schedule('refresh-location-preview', '*/10 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_storage_location_preview');
SELECT cron.schedule('refresh-location-history', '0 0 * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_storage_location_history');
```

#### Indexes
All critical indexes created on:
- Foreign keys
- PostGIS geometry columns (GIST indexes)
- Date/timestamp columns
- Status/type filter columns

#### Query Optimization
- **Bulk load**: Single query joins multiple tables
- **Detail view**: Optimized with covering indexes
- **History view**: Pre-aggregated in materialized view

### Redis Caching Strategy

#### Cache Keys
```
# Bulk load cache
cache:map:bulk-load -> TTL: 10 minutes

# Detail cache
cache:location:{id}:detail -> TTL: 1 hour

# History cache
cache:location:{id}:history:page:{page} -> TTL: 1 day

# Job status cache (from photo upload)
cache:job:{job_id}:status -> TTL: 1 second
```

#### Invalidation Strategy
- **Bulk load**: Auto-expire after 10 minutes OR manual invalidate after photo processing
- **Detail**: Invalidate after new photo processed for that location
- **History**: Invalidate after stock movement transaction

## User Experience Flow

### Flow 1: Browse Warehouses → View Internal Structure
1. **User opens app** → Map overview loads (1-2 seconds bulk load)
2. **Map displays all warehouses** as colored polygons with metrics
3. **User clicks warehouse** → Instant navigation to internal view (data already cached)
4. **Internal view shows** storage_areas and preview cards (no loading)
5. **User filters by cantero** → Instant filtering (client-side)
6. **User scrolls grid** → Lazy render preview cards (virtualization)

**Total time: < 2 seconds from open to browsing**

### Flow 2: View Storage Location Detail
1. **User clicks preview card** → API call to fetch detail (300ms)
2. **Detail view opens** showing processed image, detections, financials
3. **User examines data** → All info displayed, no further loading
4. **User clicks "View History"** → API call to fetch history (500ms)
5. **Timeline displays** with periods and charts

**Total time: 300ms for detail, 500ms additional for history**

### Flow 3: Navigate Between Locations
1. **User views location A detail** → Data fetched and cached
2. **User goes back** → Returns to warehouse internal (cached)
3. **User clicks location B** → API call for detail (300ms, cached in Redis)
4. **User goes back to location A** → Detail loaded from frontend cache (instant)

**Total time: 300ms per new location, instant for previously viewed**

## Related Diagrams

- **01_warehouse_map_overview.mmd**: Map overview with PostGIS polygons
- **02_warehouse_internal_structure.mmd**: Internal structure with storage_areas and preview cards
- **03_storage_location_preview.mmd**: Preview card component details
- **04_storage_location_detail.mmd**: Full detail view with detections and financials
- **05_historical_timeline.mmd**: Historical evolution and traceability

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial comprehensive overview |

---

**Notes:**
- Progressive detail system: Map → Warehouse → Location → History
- Bulk load strategy for levels 1-2 optimizes performance
- On-demand loading for levels 3-4 reduces initial load time
- PostGIS polygons enable geographic visualization
- Materialized views provide fast query performance
- React + Leaflet provides rich map interactions
- Full traceability via historical timeline
