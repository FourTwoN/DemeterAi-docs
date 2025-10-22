# Sales vs Stock Comparison - Detailed Flow

## Purpose

This diagram shows the **detailed implementation flow** for comparing sales data (uploaded via CSV)
with calculated stock from the database to generate estimated current stock levels.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, business analysts
- **Detail**: Complete flow from CSV upload to variance reporting
- **Mermaid Version**: v11.3.0+

## What It Represents

The complete sales comparison flow including:

1. **CSV Upload**: Multi-file upload for monthly sales data
2. **Parsing & Validation**: CSV parsing with data validation
3. **Stock Query**: Query latest active stock from database
4. **Variance Calculation**: Calculate difference (stock - sales)
5. **Report Generation**: Create comparison reports and visualizations
6. **Historical Integrity**: Ensure historical data remains unchanged

## Business Context

### The Problem

Clients take photos every 2-3 months to calculate stock. Between photo sessions, they record sales
but don't know exact current stock. They need to estimate current stock by subtracting sales from
the last calculated stock.

### The Solution

Upload CSV files with sales data (by product and packaging), query the latest active stock, and
calculate:

```
Estimated Current Stock = Last Calculated Stock - Sales
```

### Important: Historical Data Integrity

**Rule**: Only the **latest active stock** is used for calculations. Historical stock periods remain
immutable.

Example timeline:

- **Sept 1**: Photo taken → Stock A calculated
- **Sept - Nov**: Sales occur → Stock A - Sales = Estimated Stock
- **Dec 1**: New photo taken → **New stock period begins** (Stock B)
- Sales comparison now uses Stock B (Stock A becomes historical, frozen)

This ensures historical accuracy and prevents data corruption.

## CSV File Format

### Expected Format

```csv
product_sku,packaging_sku,quantity_sold,sale_date,notes
CACT-001,R7,150,2025-09-15,Monthly sales
SUCC-023,R10,200,2025-09-20,Bulk order
INJE-005,R7,75,2025-09-25,Regular client
```

### Required Columns

- `product_sku` (or `product_code`): Product SKU from `products` table
- `packaging_sku` (or `packaging_code`): Packaging SKU from `packaging_catalog`
- `quantity_sold`: Number of units sold (must be positive integer)

### Optional Columns

- `sale_date`: Date of sale (defaults to upload date)
- `notes`: Free text notes
- `customer_name`: Customer reference
- `invoice_number`: Sales invoice reference

### Validation Rules

1. **Product exists**: SKU must exist in `products` table
2. **Packaging exists**: SKU must exist in `packaging_catalog` table
3. **Quantity valid**: Must be positive integer
4. **Product-Packaging compatible**: Combination must be valid in system

### Multiple File Upload

Users can upload multiple CSV files for different months:

- `sales_september_2025.csv`
- `sales_october_2025.csv`
- `sales_november_2025.csv`

System will aggregate all sales for comparison.

## Database Tables Involved

### Sales Data (Temporary)

```sql
-- Temporary table for uploaded sales data
CREATE TEMP TABLE temp_sales_upload (
    id SERIAL PRIMARY KEY,
    upload_session_id UUID NOT NULL,
    product_id INT REFERENCES products(id),
    packaging_catalog_id INT REFERENCES packaging_catalog(id),
    quantity_sold INT CHECK (quantity_sold > 0),
    sale_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Stock Query

```sql
-- Query latest active stock
SELECT
    p.id as product_id,
    p.sku as product_sku,
    p.common_name as product_name,
    pc.name as product_category,
    pkgc.id as packaging_catalog_id,
    pkgc.sku as packaging_sku,
    pkgc.name as packaging_name,
    SUM(sb.quantity_current) as current_stock,
    MAX(pps.created_at) as last_photo_date
FROM stock_batches sb
INNER JOIN products p ON sb.product_id = p.id
INNER JOIN product_families pf ON p.family_id = pf.id
INNER JOIN product_categories pc ON pf.category_id = pc.id
INNER JOIN packaging_catalog pkgc ON sb.packaging_catalog_id = pkgc.id
INNER JOIN storage_bins sbin ON sb.current_storage_bin_id = sbin.id
INNER JOIN storage_locations sl ON sbin.storage_location_id = sl.id
INNER JOIN photo_processing_sessions pps ON sl.id = pps.storage_location_id
WHERE
    sb.quantity_current > 0  -- Active stock only
    AND pps.status = 'completed'
    AND pps.created_at = (
        SELECT MAX(created_at)
        FROM photo_processing_sessions
        WHERE storage_location_id = sl.id
          AND status = 'completed'
    )  -- Latest photo session only
GROUP BY p.id, p.sku, p.common_name, pc.name,
         pkgc.id, pkgc.sku, pkgc.name;
```

## Variance Calculation

### Formula

For each product-packaging combination:

```python
estimated_current_stock = current_stock - total_sales

variance_percentage = (total_sales / current_stock) * 100

stock_status = (
    "CRITICAL" if estimated_current_stock <= 0
    else "LOW" if estimated_current_stock < (current_stock * 0.2)
    else "MEDIUM" if estimated_current_stock < (current_stock * 0.5)
    else "OK"
)
```

### Alert Thresholds

- **CRITICAL**: Estimated stock ≤ 0 (oversold or miscalculated)
- **LOW**: Estimated stock < 20% of original
- **MEDIUM**: Estimated stock < 50% of original
- **OK**: Estimated stock ≥ 50% of original

## Report Structure

### Summary Section

```json
{
  "total_products_analyzed": 150,
  "total_stock_value_original": 125000.50,
  "total_sales_value": 45000.25,
  "total_estimated_value": 80000.25,
  "average_depletion_rate": 36.0,
  "critical_products_count": 5,
  "low_stock_count": 12,
  "last_photo_date": "2025-09-01"
}
```

### Detailed Breakdown

```json
{
  "product_sku": "CACT-001",
  "product_name": "Cactus Esférico",
  "packaging_sku": "R7",
  "packaging_name": "Maceta R7 Negra",
  "current_stock": 500,
  "total_sales": 150,
  "estimated_current_stock": 350,
  "variance_percentage": 30.0,
  "stock_status": "OK",
  "last_photo_date": "2025-09-01",
  "days_since_photo": 37,
  "unit_price": 5.50,
  "stock_value_original": 2750.00,
  "sales_value": 825.00,
  "estimated_value": 1925.00
}
```

### Discrepancies Section

Products where sales > stock (potential issues):

```json
{
  "discrepancies": [
    {
      "product_sku": "SUCC-045",
      "current_stock": 100,
      "total_sales": 150,
      "difference": -50,
      "possible_causes": [
        "Sales data includes products from previous stock period",
        "Photo session missed some stock locations",
        "Manual stock movements not recorded",
        "Product SKU mismatch in sales data"
      ],
      "recommended_action": "Review sales data or take new photo"
    }
  ]
}
```

## Visualizations

### Chart Types

1. **Stock vs Sales Comparison Bar Chart**
    - X-axis: Products
    - Y-axis: Quantity
    - Two bars: Current Stock (blue), Sales (red)
    - Third bar: Estimated Stock (green)

2. **Depletion Rate Pie Chart**
    - Categories: OK, MEDIUM, LOW, CRITICAL
    - Shows distribution of stock status

3. **Top 10 Best Sellers**
    - Horizontal bar chart
    - Sorted by sales volume

4. **Value Analysis**
    - Stacked area chart
    - Original value, Sales value, Estimated value over time

5. **Detailed Data Table**
    - All product-packaging combinations
    - Sortable, filterable, exportable

## Performance Considerations

### Large CSV Files

For files > 10,000 rows:

- Use chunked processing (1,000 rows per chunk)
- Show progress bar to user
- Process asynchronously with Celery task

```python
@celery.task
def process_sales_csv_chunk(chunk_data, upload_session_id):
    # Process 1,000 rows
    for row in chunk_data:
        validate_and_insert(row, upload_session_id)
```

### Stock Query Optimization

Use materialized view for latest active stock:

```sql
CREATE MATERIALIZED VIEW mv_latest_active_stock AS
-- ... complex query from above ...

-- Refresh after each photo processing session
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_latest_active_stock;
```

### Caching

Cache stock query results for 1 hour (stock doesn't change frequently):

```python
cache_key = f"latest_stock:snapshot"
cached_stock = redis.get(cache_key)
if not cached_stock:
    stock = await query_latest_stock(db)
    redis.setex(cache_key, 3600, json.dumps(stock))
```

## API Endpoint

```python
@router.post("/api/analytics/sales-comparison")
async def sales_vs_stock_comparison(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SalesComparisonResponse:
    """
    Upload sales CSV files and generate comparison report

    Args:
        files: One or more CSV files
        db: Database session
        current_user: Authenticated user

    Returns:
        Comparison report with summary, details, visualizations
    """
    upload_session_id = uuid4()

    # Parse and validate CSVs
    sales_data = await parse_sales_csvs(files, upload_session_id)

    # Query latest active stock
    stock_data = await query_latest_stock(db)

    # Calculate variance
    comparison = calculate_variance(stock_data, sales_data)

    # Generate visualizations
    charts = generate_comparison_charts(comparison)

    # Build response
    return SalesComparisonResponse(
        summary=comparison.summary,
        details=comparison.details,
        discrepancies=comparison.discrepancies,
        visualizations=charts,
        metadata={
            "upload_session_id": str(upload_session_id),
            "files_processed": len(files),
            "rows_processed": len(sales_data),
            "last_photo_date": stock_data.last_photo_date
        }
    )
```

## Error Handling

### Common Errors

1. **Invalid CSV Format**
   ```json
   {
     "error": "Invalid CSV format",
     "details": "Missing required column: product_sku",
     "line": 5
   }
   ```

2. **Product Not Found**
   ```json
   {
     "error": "Product not found",
     "details": "SKU 'INVALID-001' does not exist in database",
     "line": 12,
     "action": "Verify product SKU or add product to catalog"
   }
   ```

3. **Negative Stock**
   ```json
   {
     "warning": "Negative estimated stock",
     "product_sku": "CACT-005",
     "current_stock": 100,
     "sales": 150,
     "estimated": -50,
     "action": "Review sales data or take new photo"
   }
   ```

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
