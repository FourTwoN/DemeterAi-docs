# Map Warehouse Views Workflow

**Created:** 2025-10-08
**System:** DemeterAI Map Navigation & Visualization
**Total Documentation:** 4,481 lines across 6 subflows

## Overview

This workflow documents the complete **map-based warehouse navigation system** with four progressive detail levels:

1. **Level 1: Map Overview** - Geographic view of all warehouses (PostGIS polygons)
2. **Level 2: Warehouse Internal** - Storage areas (canteros) and preview cards
3. **Level 3: Storage Location Detail** - Full detail with ML detections and financials
4. **Level 4: Historical Timeline** - Evolution tracking with traceability

## Architecture Principles

### Progressive Detail System
- **Bulk load** for Levels 1-2 → Single API call, instant navigation
- **On-demand fetch** for Levels 3-4 → Separate API calls when needed
- **Client-side caching** → Redux/Zustand stores bulk-loaded data
- **Materialized views** → Pre-aggregated metrics for fast queries

### Performance Strategy

| Level | Data Loading | Response Time | Cache Strategy |
|-------|-------------|---------------|----------------|
| 1-2 (Map + Internal) | Bulk load on init | < 1s | Redis 10 min |
| 3 (Detail) | Fetch on card click | < 300ms | Redis 1 hour |
| 4 (History) | Fetch on history click | < 500ms | Redis 1 day |

## Files Structure

```
map_warehouse_views/
├── 00_comprehensive_view.md         (51 KB) - Executive overview
├── 00_comprehensive_view.mmd        (6 KB)  - High-level diagram
├── 01_warehouse_map_overview.md     (24 KB) - PostGIS polygons, map rendering
├── 01_warehouse_map_overview.mmd    (5 KB)  - Map flow diagram
├── 02_warehouse_internal_structure.md (26 KB) - Canteros, preview cards
├── 02_warehouse_internal_structure.mmd (5 KB) - Internal view diagram
├── 03_storage_location_preview.md   (16 KB) - Preview card component
├── 03_storage_location_preview.mmd  (6 KB)  - Card structure diagram
├── 04_storage_location_detail.md    (14 KB) - Full detail view
├── 04_storage_location_detail.mmd   (6 KB)  - Detail view diagram
├── 05_historical_timeline.md        (17 KB) - Evolution tracking
├── 05_historical_timeline.mmd       (7 KB)  - Timeline diagram
└── README.md                        (this file)
```

## Technology Stack

### Frontend
- **React** - UI framework
- **Leaflet** - Map rendering library
- **react-leaflet** - React bindings for Leaflet
- **Recharts** - Charts for historical data
- **react-window** - Virtualization for large lists
- **Zustand/Redux** - State management

### Backend
- **FastAPI** - REST API framework
- **PostgreSQL** - Primary database
- **PostGIS** - Geographic data extension
- **Redis** - Caching layer
- **Celery** - Background ML processing

### Database
- **PostGIS GEOMETRY** - Warehouse polygons (SRID 4326)
- **Materialized Views** - Pre-aggregated metrics
- **pg_cron** - Scheduled view refreshes

## Key Database Objects

### Tables
- `warehouses` - Warehouse master data with PostGIS polygons
- `storage_areas` - Canteros (N, S, E, W, C)
- `storage_locations` - Individual storage spots (claros)
- `photo_processing_sessions` - ML processing results
- `stock_batches` - Current inventory
- `stock_movements` - Movement tracking (plantar, muerte, ventas, etc.)

### Materialized Views
- `mv_warehouse_summary` - Warehouse metrics (refresh: 5 min)
- `mv_storage_location_preview` - Preview card data (refresh: 10 min)
- `mv_storage_location_history` - Historical timeline (refresh: daily)

## API Endpoints

### Level 1-2: Bulk Load
```
GET /api/v1/map/bulk-load
Response: warehouses + storage_areas + storage_locations (with preview data)
Performance: < 1s, cached 10 min
```

### Level 3: Detail View
```
GET /api/v1/storage-locations/{id}/detail
Response: Full detail with detections, financials, quality metrics
Performance: < 300ms, cached 1 hour
```

### Level 4: Historical Timeline
```
GET /api/v1/storage-locations/{id}/history?page=1&per_page=12
Response: Periods with movements (fecha, plantados, muertes, vendidos, etc.)
Performance: < 500ms, cached 1 day
```

## User Journey

### Happy Path: Browse → Explore → Detail → History

1. **User opens app** → Bulk load (1-2s)
2. **Map displays** → All warehouses as PostGIS polygons
3. **User clicks warehouse** → Instant navigation (data cached)
4. **Internal view shows** → Canteros + preview cards grid
5. **User clicks preview card** → Fetch detail (~300ms)
6. **Detail view opens** → Image, detections, financials
7. **User clicks "View History"** → Fetch timeline (~500ms)
8. **Timeline displays** → Periods, charts, movements

**Total time: 2s initial + 300ms detail + 500ms history = ~3s end-to-end**

## PostGIS Integration

### Coordinate System
- **SRID 4326** - WGS84 (standard GPS coordinates)
- **Format**: [longitude, latitude] in GeoJSON
- **Conversion**: Leaflet uses [latitude, longitude]

### Key PostGIS Functions
```sql
-- Convert GEOMETRY to GeoJSON
ST_AsGeoJSON(geojson_coordinates)

-- Calculate centroid (auto-generated)
ST_Centroid(geojson_coordinates)

-- Calculate area in square meters
ST_Area(geojson_coordinates::geography)

-- Find location by GPS coordinates
ST_DWithin(centroid::geography, ST_MakePoint(lon, lat)::geography, 10)

-- Check if point is within polygon
ST_Intersects(geojson_coordinates, point_geometry)
```

## Performance Optimization

### Database Level
- **Materialized views** with concurrent refresh
- **GIST indexes** on PostGIS geometry columns
- **Composite indexes** on frequently filtered columns
- **Generated columns** for centroid and area_m2

### API Level
- **Redis caching** with appropriate TTLs
- **GZIP compression** for JSON responses
- **Batch queries** to reduce round trips
- **Pagination** for large datasets

### Frontend Level
- **Bulk load strategy** eliminates multiple requests
- **Client-side filtering** for instant responsiveness
- **Lazy image loading** with `loading="lazy"`
- **React.memo** to prevent unnecessary re-renders
- **Virtualization** for 500+ items (react-window)

## Metrics & KPIs

### System Performance
- **Initial load**: < 1s (bulk load)
- **Map render**: < 100ms (PostGIS to Leaflet)
- **Detail fetch**: < 300ms (cached)
- **History fetch**: < 500ms (materialized view)

### Data Freshness
- **Warehouse summary**: 5 min (materialized view refresh)
- **Preview data**: 10 min (materialized view refresh)
- **Historical data**: Daily (materialized view refresh)

### Cache Hit Rates
- **Bulk load**: 95%+ (10 min TTL)
- **Detail**: 90%+ (1 hour TTL)
- **History**: 99%+ (1 day TTL)

## Movement Types & Traceability

### Movement Types
- **plantar** - New plants added from nursery
- **sembrar** - Seeds sown, start of cycle
- **transplante** - Moved to another location
- **muerte** - Deaths, discards, pest damage
- **ventas** - Sold to customers
- **foto** - Photo capture, ML detection
- **ajuste** - Manual inventory adjustment

### Audit Trail
Every movement includes:
- `created_by_user_id` - Who made the change
- `created_at` - When it occurred
- `reference_session_id` - Link to photo session
- `notes` - Optional comments

## Quality Metrics

### Storage Location Quality
- **Overall score** (0-100) - Weighted average from stock_batches
- **Health score** - Plant health indicator
- **Growth rate** - % increase over time
- **Mortality rate** - % deaths over time

### Color Coding
- **Green (80-100)** - Excellent, healthy
- **Yellow (60-79)** - Good, acceptable
- **Red (< 60)** - Needs attention

## Financial Calculations

### Current Value
```typescript
current_value = quantity_current × cost_per_unit
```

### Potential Value (30% growth estimate)
```typescript
potential_value = current_value × 1.3
```

### ROI Percentage
```typescript
roi_percent = ((potential_value - current_value) / current_value) × 100
```

## Visualization Features

### Map Overview
- **PostGIS polygons** rendered as Leaflet Polygons
- **Color-coded** by warehouse type (greenhouse, shadehouse, etc.)
- **Hover tooltips** with name and metrics
- **Click popup** with detailed stats and "View Internal" button

### Preview Cards
- **Thumbnail** (300×300px) from S3
- **Trend indicators** (↑↓→) with percentage change
- **Status badges** (green/yellow/red)
- **Category breakdown** (cactus, suculenta, injerto)
- **Financial summary** (current + potential value)

### Historical Charts
- **Line chart** - Quantity evolution over time
- **Bar chart** - Movement breakdown by type
- **Period cards** - Detailed metrics per period

## Error Handling

### Database Errors
- **Connection timeout** → Retry with exponential backoff
- **Query timeout** → Return partial results or cached data
- **Materialized view refresh failure** → Alert admin, use stale data

### API Errors
- **500 Internal Server Error** → Show error message, retry button
- **404 Not Found** → Show "Not found" message, back button
- **Network timeout** → Show loading state, auto-retry

### Frontend Errors
- **Image load failure** → Show placeholder with "No photo" text
- **Map render error** → Fallback to list view
- **State hydration failure** → Force refresh, reload from API

## Future Enhancements

### Short Term
- **Viewport filtering** - Only load warehouses in map bounds (for 100+ warehouses)
- **Real-time updates** - WebSocket connection for live inventory changes
- **Offline support** - Service worker for offline map viewing

### Medium Term
- **3D visualization** - Three.js for warehouse interior 3D models
- **AR navigation** - Mobile AR for finding storage locations
- **Predictive analytics** - ML models for mortality/growth predictions

### Long Term
- **Multi-facility** - Cross-facility inventory management
- **Automated routing** - Optimal picking paths for order fulfillment
- **Integration** - ERP/WMS system integration

## Testing Strategy

### Unit Tests
- PostGIS query functions
- Financial calculations
- Movement balance verification

### Integration Tests
- API endpoints with database
- Materialized view refresh
- Cache invalidation

### E2E Tests
- Map overview → internal view → detail → history
- Filter and search functionality
- Image loading and error states

## Documentation Standards

### Markdown Files
- **Purpose section** - What the subflow represents
- **Scope section** - Level, audience, technology
- **Database schema** - Tables, indexes, constraints
- **API endpoints** - Request/response examples
- **Code examples** - TypeScript/Python implementation
- **Performance metrics** - Response times, cache strategies

### Mermaid Diagrams
- **v11.3.0+ syntax** - Modern Mermaid features
- **Clear flow** - Left-to-right or top-to-bottom
- **Subgraphs** - Group related components
- **Color coding** - Consistent colors per component type
- **Labels** - Descriptive node labels with metrics

## Maintenance

### Daily
- Monitor materialized view refresh logs
- Check API response times
- Review error logs

### Weekly
- Analyze cache hit rates
- Review user navigation patterns
- Update documentation for new features

### Monthly
- Optimize slow queries
- Review and adjust cache TTLs
- Update materialized view refresh schedules

## Contributors

**Initial Documentation:** Claude (Anthropic)
**Date:** October 8, 2025
**Version:** 1.0.0

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial complete workflow documentation |

---

**Total Documentation:** 12 files, 4,481 lines, comprehensive coverage of map warehouse views system.
