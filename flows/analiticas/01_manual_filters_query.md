# Manual Filtering Analytics - Detailed Flow

## Purpose

This diagram shows the **detailed implementation flow** for manual filtering analytics, where users select filters through the UI to generate reports and visualizations from the cultivation database.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, database engineers
- **Detail**: Complete flow from UI interaction to query execution and visualization
- **Mermaid Version**: v11.3.0+

## What It Represents

The complete manual analytics flow including:

1. **Filter Selection**: User interface for selecting analysis parameters
2. **Query Building**: Dynamic SQL construction based on selected filters
3. **Query Execution**: Database query with optimizations
4. **Data Aggregation**: Result processing and aggregation
5. **Visualization**: Chart and table generation
6. **Caching**: Redis caching for performance

## Available Filters

### Geographic Filters
- **Warehouse**: Filter by one or multiple warehouses
- **Storage Area**: Filter by cantero (N, S, E, W, C)
- **Storage Location**: Filter by specific claros
- **Storage Bin**: Filter by individual bins (boxes/plugs)

### Product Filters
- **Product Category**: cactus, suculenta, injerto
- **Product Family**: Filter by botanical family
- **Product**: Specific product/species
- **Product Size**: Small, medium, large
- **Product State**: germinado, plantín, ready_to_sell, etc.

### Packaging Filters
- **Packaging Type**: pot, tray, plug
- **Packaging Catalog**: Specific pot sizes (R7, R10, etc.)
- **Packaging Color**: Filter by pot color

### Temporal Filters
- **Date Range**: From/To dates
- **Photo Session**: Filter by specific processing sessions
- **Stock Movement Period**: Analyze movements in time range

### Analysis Type
- **Current Stock**: Show current stock levels
- **Stock Movements**: Show historical movements (transplante, muerte, ventas)
- **Mortality Analysis**: Calculate and show mortality rates
- **Occupancy Analysis**: Storage location utilization
- **Value Analysis**: Calculate stock value using price_list

## Database Tables Involved

### Primary Tables
```sql
-- Geographic hierarchy
warehouses (id, code, name, geojson_coordinates)
storage_areas (id, warehouse_id, code, position)
storage_locations (id, storage_area_id, code, qr_code)
storage_bins (id, storage_location_id, storage_bin_type_id)

-- Stock data
stock_batches (id, current_storage_bin_id, product_id,
               product_state_id, product_size_id,
               packaging_catalog_id, quantity_current, quality_score)
stock_movements (id, batch_id, movement_type, quantity,
                 created_at, source_type)

-- Product catalog
products (id, family_id, sku, common_name)
product_families (id, category_id, name)
product_categories (id, code, name)
product_states (id, code, name, is_sellable)
product_sizes (id, code, name)

-- Packaging and pricing
packaging_catalog (id, packaging_type_id, sku, name, volume_liters)
price_list (id, packaging_catalog_id, product_categories_id,
            retail_unit_price, wholesale_unit_price)

-- Photo processing
photo_processing_sessions (id, storage_location_id,
                          total_detected, status, created_at)
```

## Query Building Strategy

### Base Query Template
```sql
SELECT
    -- Aggregations based on analysis type
    COUNT(*) as total_count,
    SUM(sb.quantity_current) as total_quantity,
    AVG(sb.quality_score) as avg_quality,
    -- Pricing if requested
    SUM(sb.quantity_current * pl.retail_unit_price) as total_value
FROM stock_batches sb
INNER JOIN storage_bins sbin ON sb.current_storage_bin_id = sbin.id
INNER JOIN storage_locations sl ON sbin.storage_location_id = sl.id
INNER JOIN storage_areas sa ON sl.storage_area_id = sa.id
INNER JOIN warehouses w ON sa.warehouse_id = w.id
LEFT JOIN products p ON sb.product_id = p.id
LEFT JOIN product_families pf ON p.family_id = pf.id
LEFT JOIN product_categories pc ON pf.category_id = pc.id
LEFT JOIN packaging_catalog pkgc ON sb.packaging_catalog_id = pkgc.id
LEFT JOIN price_list pl ON pl.packaging_catalog_id = pkgc.id
    AND pl.product_categories_id = pc.id
WHERE
    sb.quantity_current > 0  -- Active stock only
    -- Dynamic filters added here
GROUP BY
    -- Group by based on requested dimensions
ORDER BY
    -- Order by based on requested sorting
```

### Dynamic Filter Injection

Filters are added dynamically based on user selection:

```python
# Example filter building
filters = []
params = {}

if warehouse_ids:
    filters.append("w.id IN :warehouse_ids")
    params['warehouse_ids'] = warehouse_ids

if storage_area_ids:
    filters.append("sa.id IN :storage_area_ids")
    params['storage_area_ids'] = storage_area_ids

if product_category_ids:
    filters.append("pc.id IN :product_category_ids")
    params['product_category_ids'] = product_category_ids

if date_from and date_to:
    filters.append("pps.created_at BETWEEN :date_from AND :date_to")
    params['date_from'] = date_from
    params['date_to'] = date_to

# Combine filters
where_clause = " AND ".join(filters)
```

## Performance Optimizations

### 1. Materialized Views

Pre-computed aggregations for common queries:

```sql
CREATE MATERIALIZED VIEW mv_current_stock_summary AS
SELECT
    w.id as warehouse_id,
    w.name as warehouse_name,
    sa.id as storage_area_id,
    sa.name as storage_area_name,
    pc.id as product_category_id,
    pc.name as product_category_name,
    COUNT(DISTINCT sl.id) as location_count,
    COUNT(DISTINCT sb.id) as batch_count,
    SUM(sb.quantity_current) as total_quantity,
    AVG(sb.quality_score) as avg_quality,
    MAX(pps.created_at) as last_photo_date
FROM stock_batches sb
-- ... joins ...
WHERE sb.quantity_current > 0
GROUP BY w.id, w.name, sa.id, sa.name, pc.id, pc.name;

-- Refresh strategy: CONCURRENTLY after photo processing
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_current_stock_summary;
```

### 2. Indexes

Optimized indexes for filtering:

```sql
CREATE INDEX idx_stock_batches_current_bin ON stock_batches(current_storage_bin_id);
CREATE INDEX idx_stock_batches_product ON stock_batches(product_id);
CREATE INDEX idx_stock_batches_quantity ON stock_batches(quantity_current) WHERE quantity_current > 0;
CREATE INDEX idx_stock_movements_created_at ON stock_movements(created_at);
CREATE INDEX idx_storage_bins_location ON storage_bins(storage_location_id);
```

### 3. Redis Caching

Cache frequent queries:

```python
# Cache key format
cache_key = f"analytics:filters:{hash(filter_params)}"
cache_ttl = 300  # 5 minutes

# Check cache first
cached_result = redis.get(cache_key)
if cached_result:
    return json.loads(cached_result)

# Execute query
result = await db.execute(query, params)

# Cache result
redis.setex(cache_key, cache_ttl, json.dumps(result))
```

## Visualization Types

### Chart Types by Analysis
- **Stock Distribution**: Pie chart, stacked bar chart
- **Temporal Trends**: Line chart, area chart
- **Geographic Comparison**: Grouped bar chart, heatmap
- **Mortality Analysis**: Bar chart with percentages
- **Value Analysis**: Currency-formatted tables, bar charts

### Frontend Libraries
- **Chart.js**: Primary charting library
- **AG Grid**: Advanced data tables with sorting/filtering
- **Export**: Chart.js PNG export, table to Excel

## Example Queries

### Query 1: Stock by Warehouse and Category
```sql
SELECT
    w.name as warehouse,
    pc.name as category,
    COUNT(DISTINCT sl.id) as locations,
    SUM(sb.quantity_current) as total_quantity,
    SUM(sb.quantity_current * pl.retail_unit_price) as total_value
FROM stock_batches sb
-- ... joins ...
WHERE sb.quantity_current > 0
  AND w.id IN (1, 2, 3)
GROUP BY w.name, pc.name
ORDER BY total_value DESC;
```

### Query 2: Mortality Rate by Storage Area
```sql
SELECT
    sa.name as storage_area,
    COUNT(*) FILTER (WHERE sm.movement_type = 'muerte') as deaths,
    COUNT(*) FILTER (WHERE sm.movement_type = 'foto') as initial_count,
    ROUND(
        COUNT(*) FILTER (WHERE sm.movement_type = 'muerte')::numeric /
        NULLIF(COUNT(*) FILTER (WHERE sm.movement_type = 'foto'), 0) * 100,
        2
    ) as mortality_rate_pct
FROM stock_movements sm
INNER JOIN stock_batches sb ON sm.batch_id = sb.id
-- ... joins ...
WHERE sm.created_at BETWEEN :date_from AND :date_to
GROUP BY sa.name
ORDER BY mortality_rate_pct DESC;
```

## API Endpoint

```python
@router.post("/api/analytics/manual-query")
async def manual_analytics_query(
    filters: AnalyticsFilters,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> AnalyticsResponse:
    """
    Execute manual analytics query with filters

    Args:
        filters: Filter parameters from frontend
        db: Database session
        redis: Redis cache

    Returns:
        Aggregated data + visualization config
    """
    # Build query
    query = build_analytics_query(filters)

    # Check cache
    cache_key = f"analytics:{hash(filters)}"
    cached = await redis.get(cache_key)
    if cached:
        return AnalyticsResponse.parse_raw(cached)

    # Execute
    result = await db.execute(query)
    data = result.all()

    # Generate visualization config
    viz_config = generate_chart_config(data, filters.chart_type)

    # Build response
    response = AnalyticsResponse(
        data=data,
        visualization=viz_config,
        metadata={
            "row_count": len(data),
            "execution_time_ms": ...,
            "cached": False
        }
    )

    # Cache for 5 minutes
    await redis.setex(cache_key, 300, response.json())

    return response
```

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Simple query (< 10K rows) | < 200ms | Using indexes |
| Complex query (< 100K rows) | < 500ms | Using materialized views |
| Large query (> 100K rows) | < 2s | Pagination required |
| Cache hit | < 50ms | Redis lookup |
| Chart generation | < 100ms | Frontend Chart.js |

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
