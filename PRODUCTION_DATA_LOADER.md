# Production Data Loader

## Overview

The Production Data Loader is a system for loading geospatial and catalog data from GeoJSON and CSV files into the DemeterAI database. It enables seamless initialization of the database with real production data including GPS coordinates, product categories, packaging information, and pricing data.

**Key Features:**
- ✅ Idempotent - Safe to run multiple times without creating duplicates
- ✅ Dependency-aware - Loads data in correct order
- ✅ Error-resilient - Logs errors but continues processing
- ✅ Flexible - Works in both development and production modes
- ✅ Complete - Loads all production data types in one operation

## Architecture

### Modes

#### 1. Development Mode (Default)
- **What happens**: Database tables are DROPPED and RECREATED on every startup
- **Data**: All existing data is lost
- **Use case**: Development and testing
- **Command**: Just start the app normally (or set `LOAD_PRODUCTION_DATA=false`)

#### 2. Production Data Mode
- **What happens**: Database tables are created ONCE, then production data is loaded
- **Data**: Preserved and updated with production data
- **Use case**: Loading real inventory, pricing, and location data
- **Command**: Set environment variable `LOAD_PRODUCTION_DATA=true`

### Data Load Order

The loader processes data in dependency order to maintain referential integrity:

1. **Warehouses** (from `naves.geojson`)
   - Top-level geographic container
   - Example: "Nave 1", "Nave 2", "Nave 3"

2. **StorageAreas** (from `canteros.geojson`)
   - Subdivisions within warehouses
   - Example: "Cantero Norte", "Cantero Sur"
   - Foreign key: References Warehouse

3. **StorageLocations** (from `claros.geojson`)
   - Photo capture points within storage areas
   - Example: "Claro 1", "Claro 2"
   - Foreign key: References StorageArea
   - Note: Extracts POINT geometry from GeoJSON

4. **ProductCategories** (from CSV files)
   - Root level of product taxonomy
   - Example: "CACTUS", "SUCCULENT", "BROMELIAD"
   - Sources:
     - `product_category/categories.csv`
     - `product_category/categories_2.csv`

5. **StorageBinTypes** (Hardcoded Seed Data)
   - Container/bin type catalog
   - **4 Required Types**:
     - `SEGMENTO` - Individual segment (no grid)
     - `PLUGS` - 288-cell plug tray (18×16 grid)
     - `ALMACIGOS` - Seedling tray (10×10 grid)
     - `CAJONES` - Transport box (no grid)

6. **PriceList** (from `price_list/price_list.csv`)
   - Pricing by packaging and product category
   - Foreign keys: PackagingCatalog + ProductCategory
   - Only loaded if both parent records exist

## Data Source Files

### GeoJSON Files (`production_data/gps_layers/`)

#### `naves.geojson` → Warehouses
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [...]},
      "properties": {"Nave": "Nave 1", ...}
    }
  ]
}
```

**Properties:**
- `Nave` - Warehouse name (e.g., "Nave 1")
- Geometry: POLYGON (boundary coordinates)

**Result:**
- Creates Warehouse records
- Code generated from name (e.g., "NAVE1")
- Type defaults to "greenhouse"

#### `canteros.geojson` → StorageAreas
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [...]},
      "properties": {"Cantero": "Cantero Norte", ...}
    }
  ]
}
```

**Properties:**
- `Cantero` - Storage area name (e.g., "Cantero Norte")
- Geometry: POLYGON (boundary coordinates)

**Result:**
- Creates StorageArea records
- Code pattern: `WAREHOUSE-AREA` (e.g., "NAVE1-CANTERO_NORTE")
- Position defaults to "N" (North)

#### `claros.geojson` → StorageLocations
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [...]},
      "properties": {"Claro": "Claro 1", ...}
    }
  ]
}
```

**Properties:**
- `Claro` - Location name (e.g., "Claro 1")
- Geometry: POLYGON or POINT (converts polygon to centroid POINT)

**Result:**
- Creates StorageLocation records
- Code pattern: `WAREHOUSE-AREA-LOC-###` (e.g., "NAVE1-CANTERO_NORTE-LOC-001")
- QR code: `LOC#####` (e.g., "LOC00001")
- Coordinates stored as POINT

### CSV Files

#### `product_category/categories.csv`
Product category classifications

**Format:**
```
Column 0: Category type (SUCCULENT, CACTUS, etc.)
Column 1: Genus (haworthia, echeveria, etc.)
Column 2: Species/variety description
...
```

**Example:**
```
SR5D,haworthia,resendeana
SR5D,haworthia,parecida a resendeana 1
CACTUS,mammillaria,camptotricha
```

**Result:**
- Extracts unique values from Column 0
- Creates ProductCategory records with code from category type
- Auto-uppercases codes (e.g., "cactus" → "CACTUS")

#### `product_category/categories_2.csv`
Additional product categories with similar structure

**Result:**
- Merged with categories.csv
- Deduplicates by code

#### `price_list/price_list.csv`
Product pricing by packaging and category

**Format:**
```
Header rows (3): Skip
Column 0: Category (CACTUS, SUCCULENT, etc.)
Column 1: Packaging/Pot type (Rígida 5, Soplada, etc.)
Column 2: Unit price ($950, $1.05, etc.)
Column 3: SKU (C R5 T-1, C R5 D-2, etc.)
Column 4: Units per box (45, 28, etc.)
...
```

**Example:**
```
CACTUS,Rígida 5 cuadrada terracota,$950,C R5 T-1,45,...
CACTUS,Rígida cuadrada 5 dorada,$1.05,C R5 D-2,45,...
```

**Result:**
- Requires ProductCategory to exist (matched by name)
- Requires PackagingCatalog to exist (matched by description)
- Creates PriceList records with wholesale and retail pricing

## Usage

### Option 1: Environment Variable (Recommended)

Set environment variable before starting the application:

```bash
# Load production data
LOAD_PRODUCTION_DATA=true python -m uvicorn app.main:app --reload

# Or for development mode (drop + recreate)
LOAD_PRODUCTION_DATA=false python -m uvicorn app.main:app --reload

# Or use Docker Compose
# Edit .env or docker-compose.yml to set LOAD_PRODUCTION_DATA=true
docker-compose up
```

### Option 2: Code Configuration

Edit `app/main.py` in the `startup_event()` function:

```python
# Option 1: Use environment variable (default)
load_prod_data = os.getenv("LOAD_PRODUCTION_DATA", "false").lower() == "true"

# Option 2: Uncomment to always load production data
# load_prod_data = True

# Option 3: Uncomment for development mode (drop + recreate)
# load_prod_data = False
```

### Option 3: Direct Function Call

For programmatic control, you can call the loader directly:

```python
from sqlalchemy.orm import Session
from app.db.load_production_data import ProductionDataLoader

async def load_data(session: Session):
    loader = ProductionDataLoader(session)
    counts = await loader.load_all_async()

    print(f"Loaded: {counts}")
    # Output: Loaded: {
    #   'warehouses': 3,
    #   'storage_areas': 12,
    #   'storage_locations': 48,
    #   'product_categories': 15,
    #   'storage_bin_types': 4,
    #   'price_list': 285
    # }
```

## Data Import Workflow

### 1. Initial Setup (Development Mode)
```bash
# Create database with empty schema
LOAD_PRODUCTION_DATA=false python -m uvicorn app.main:app --reload
# Visit http://localhost:8000/docs to verify API works
# Stop the server (Ctrl+C)
```

### 2. Load Production Data
```bash
# Switch to production data mode
LOAD_PRODUCTION_DATA=true python -m uvicorn app.main:app --reload
# Application starts, loads all production data
# Check logs for: "✅ Production data load complete!"
```

### 3. Verify Data
```bash
# Query the API or database directly
psql -d demeterai_test -c "SELECT COUNT(*) FROM warehouses;"
psql -d demeterai_test -c "SELECT COUNT(*) FROM product_categories;"
psql -d demeterai_test -c "SELECT COUNT(*) FROM storage_bin_types;"
```

### 4. Add More Data (Optional)
```bash
# Add CSV files to production_data/ folder
# Restart the application
LOAD_PRODUCTION_DATA=true python -m uvicorn app.main:app --reload
# New data is loaded, existing data is preserved (idempotent)
```

## Data Validation

The loader validates data before insertion:

- ✅ Checks for duplicate codes (prevents duplicate inserts)
- ✅ Validates GeoJSON geometry (converts Polygons to POINT for StorageLocation)
- ✅ Validates CSV format (handles missing columns gracefully)
- ✅ Validates foreign keys (only creates records if parent exists)
- ✅ Handles encoding issues (logs errors and continues)

## Logging

The loader provides detailed logging at each step:

```
🚀 Loading production data...
✨ Creating tables if they don't exist...
  No tables found, creating all tables from models...
✅ All tables created successfully
Loading warehouses from /path/to/naves.geojson...
  ✓ Warehouse: Nave 1 (NAVE1)
  ✓ Warehouse: Nave 2 (NAVE2)
  ✓ Warehouse: Nave 3 (NAVE3)
✅ Loaded 3 warehouses
...
✅ Production data load complete!
Loaded: {
  'warehouses': 3,
  'storage_areas': 12,
  'storage_locations': 48,
  'product_categories': 15,
  'storage_bin_types': 4,
  'price_list': 285
}
```

## Idempotency

The loader is **idempotent** - it's safe to run multiple times:

- ✅ Checks if record exists before inserting
- ✅ Only creates new records (doesn't overwrite)
- ✅ Updates can be done manually via API
- ✅ Errors in one row don't stop processing

This means you can safely run the loader multiple times during development:

```bash
# First run: Loads all data
LOAD_PRODUCTION_DATA=true uvicorn app.main:app

# Second run: Only loads NEW data (idempotent)
LOAD_PRODUCTION_DATA=true uvicorn app.main:app

# Third run: No new data to load
LOAD_PRODUCTION_DATA=true uvicorn app.main:app
```

## File Structure

```
production_data/
├── gps_layers/
│   ├── naves.geojson          → Warehouses (3-5 records)
│   ├── canteros.geojson        → StorageAreas (10-15 records)
│   └── claros.geojson          → StorageLocations (40-60 records)
├── product_category/
│   ├── categories.csv          → Product taxonomy (Part 1)
│   └── categories_2.csv        → Product taxonomy (Part 2)
└── price_list/
    └── price_list.csv          → Pricing data (200-400 records)
```

## Troubleshooting

### "Warehouses file not found"
**Problem**: GeoJSON file doesn't exist
**Solution**:
```bash
ls -la production_data/gps_layers/
# Should show: naves.geojson, canteros.geojson, claros.geojson
```

### "No warehouse found. Load warehouses first."
**Problem**: StorageArea loader can't find parent Warehouse
**Solution**: Check logs for warehouse loading errors, ensure naves.geojson exists

### "Category not found: CACTUS"
**Problem**: ProductCategory doesn't exist in database
**Solution**: Check product_category CSV files are valid, check for parsing errors in logs

### "Packaging not found: Rígida 5"
**Problem**: PackagingCatalog doesn't exist for price_list entry
**Solution**: Create PackagingCatalog records first (separate from production data loader)

### Database Connection Error
**Problem**: Can't connect to database
**Solution**:
```bash
# Check database is running
docker-compose ps

# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

## Advanced Usage

### Load Only Specific Data Types

```python
from sqlalchemy.orm import Session
from app.db.load_production_data import ProductionDataLoader

async def load_warehouses_only(session: Session):
    loader = ProductionDataLoader(session)
    count = await loader.load_warehouses_async()
    print(f"Loaded {count} warehouses")

async def load_categories_only(session: Session):
    loader = ProductionDataLoader(session)
    count = await loader.load_product_categories_async()
    print(f"Loaded {count} categories")
```

### Custom Data Files

To use different GeoJSON or CSV files:

1. Update file paths in `ProductionDataLoader.__init__()`:
```python
CUSTOM_DATA_DIR = Path(__file__).parent.parent.parent / "my_custom_data"
```

2. Or pass custom session with data:
```python
loader = ProductionDataLoader(custom_session)
count = await loader.load_warehouses_async()
```

### Dry Run (Preview Data)

```python
# Read without inserting (modify loader to skip session.add())
async def preview_data(session: Session):
    with open(PRODUCTION_DATA_DIR / "gps_layers" / "naves.geojson") as f:
        data = json.load(f)
        for feature in data["features"]:
            print(f"Would load: {feature['properties']}")
```

## Performance

Typical load times on modern hardware:

| Data Type | Records | Time |
|-----------|---------|------|
| Warehouses | 3-5 | <100ms |
| StorageAreas | 10-15 | <200ms |
| StorageLocations | 40-60 | <500ms |
| ProductCategories | 15-20 | <300ms |
| StorageBinTypes | 4 | <50ms |
| PriceList | 200-400 | <2s |
| **Total** | **~500** | **<3s** |

## Next Steps

After loading production data:

1. **Verify Data**: Query API endpoints to ensure data is correct
2. **Add More Data**: Add users, products, stock batches via API
3. **Test ML Pipeline**: Upload photos to test detection and estimation
4. **Configure Pricing**: Adjust price_list entries as needed
5. **Setup Dashboards**: Create analytics queries for inventory monitoring

## Architecture Reference

See related documentation:
- `app/db/load_production_data.py` - Loader implementation
- `app/db/init_db.py` - Database initialization
- `app/main.py` - Application startup
- `database/database.mmd` - Database schema/ERD
- `production_data/` - Data files

## Support

For issues or questions:

1. Check logs: Look for error messages in startup output
2. Check data files: Verify CSV/JSON format is correct
3. Check database: Connect directly to verify schema
4. Check model definitions: Review app/models/*.py for field requirements

---

**Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Production Ready ✅
