# QUICK REFERENCE: PRODUCTION DATA LOADER ERRORS

## 5 CRITICAL ERRORS AT A GLANCE

```
ERROR 1: Line 1549
┌─────────────────────────────────────────────────────┐
│ stmt = select(PackagingCatalog).where(              │
│     PackagingCatalog.description.ilike(...)  ❌     │
│                      ^^^^^^^^^^ NO EXISTE           │
│ SHOULD BE: PackagingCatalog.name                    │
└─────────────────────────────────────────────────────┘

ERROR 2: Line 1557
┌─────────────────────────────────────────────────────┐
│ packaging = PackagingCatalog(                       │
│     code=sku[:20] if sku else f"PKG{count:04d}",   │
│     ^^^^ NO EXISTE                                  │
│ SHOULD BE: sku=sku[:50] ...                         │
└─────────────────────────────────────────────────────┘

ERROR 3: Line 1558
┌─────────────────────────────────────────────────────┐
│ packaging = PackagingCatalog(                       │
│     description=maceta[:200],  ❌ NO EXISTE        │
│     ^^^^^^^^^^^ SHOULD BE: name=maceta[:200]        │
└─────────────────────────────────────────────────────┘

ERROR 4: Line 1556 (MISSING FIELDS)
┌─────────────────────────────────────────────────────┐
│ packaging = PackagingCatalog(                       │
│     # MISSING REQUIRED FIELDS:                     │
│     # packaging_type_id (FK NOT NULL)              │
│     # packaging_material_id (FK NOT NULL)          │
│     # packaging_color_id (FK NOT NULL)             │
│     # sku (NOT NULL)                               │
│     # name (NOT NULL)                              │
│     code=...,          ❌ WRONG                     │
│     description=...,   ❌ WRONG                     │
│ )                                                   │
│                                                     │
│ RESULT: IntegrityError - NOT NULL constraint       │
└─────────────────────────────────────────────────────┘

ERROR 5: Line 216-222 (CASCADE FAILURE)
┌─────────────────────────────────────────────────────┐
│ load_warehouses() → 0 (fails silently)              │
│   ↓                                                 │
│ load_storage_areas() → tries to use default_warehouse
│   ↓ (but warehouse is None!)                       │
│ Returns 0 early                                     │
│   ↓ (cascading failure)                            │
│ load_storage_location_config() → depends on        │
│ storage_areas which are 0                          │
└─────────────────────────────────────────────────────┘
```

---

## WHAT ACTUALLY EXISTS IN PackagingCatalog

```
✅ FIELDS THAT EXIST:
├─ id (PK)
├─ packaging_type_id (FK, NOT NULL)
├─ packaging_material_id (FK, NOT NULL)
├─ packaging_color_id (FK, NOT NULL)
├─ sku (VARCHAR(50), UNIQUE, NOT NULL)
├─ name (VARCHAR(200), NOT NULL)
├─ volume_liters (NUMERIC, NULLABLE)
├─ diameter_cm (NUMERIC, NULLABLE)
└─ height_cm (NUMERIC, NULLABLE)

❌ FIELDS THAT DON'T EXIST (BUT CODE TRIES TO USE):
├─ code
└─ description
```

---

## IMPORT TEST

```bash
# This will FAIL with AttributeError:
python3 << 'PYTHON'
from app.models import PackagingCatalog
print(PackagingCatalog.description)  # ❌ AttributeError
PYTHON

# This will WORK:
python3 << 'PYTHON'
from app.models import PackagingCatalog
print(PackagingCatalog.name)  # ✅ OK
print(PackagingCatalog.sku)   # ✅ OK
PYTHON
```

---

## HOW TO VERIFY THE FIX

```bash
# After implementing fixes:
python3 << 'PYTHON'
import asyncio
from app.db.load_production_data import ProductionDataLoader
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

async def test():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        loader = ProductionDataLoader(session)
        results = await loader.load_all_async()
        
        print("\nRESULTS:")
        for key, count in results.items():
            status = "✅" if count > 0 else "❌"
            print(f"{status} {key}: {count}")

asyncio.run(test())
PYTHON
```

**BEFORE (CURRENT):**
```
❌ warehouses: 0
❌ storage_areas: 0
✅ storage_locations: 12
❌ product_categories: 0
❌ product_states: 0
❌ product_families: 0
❌ products: 0
❌ storage_bin_types: 0
❌ storage_location_config: 0
❌ price_list: 0
```

**AFTER (EXPECTED WITH FIXES):**
```
✅ warehouses: 8
✅ storage_areas: 8-10
✅ storage_locations: 12
✅ product_categories: 5+
✅ product_states: 11
✅ product_families: 20
✅ products: 5
✅ storage_bin_types: 4
✅ storage_location_config: 1+
✅ price_list: 100+
```

---

## MINIMAL FIX (5 MINUTES)

If you only want to fix the AttributeError immediately:

### File: app/db/load_production_data.py

**Line 1549 - CHANGE:**
```python
# BEFORE
stmt = select(PackagingCatalog).where(
    PackagingCatalog.description.ilike(f"%{maceta}%")
)

# AFTER
stmt = select(PackagingCatalog).where(
    PackagingCatalog.name.ilike(f"%{maceta}%")
)
```

**Line 1557 - CHANGE:**
```python
# BEFORE
packaging = PackagingCatalog(
    code=sku[:20] if sku else f"PKG{count:04d}",
    description=maceta[:200],
)

# AFTER
packaging = PackagingCatalog(
    sku=sku[:50] if sku else f"PKG{count:04d}",
    name=maceta[:200],
    # PROBLEM: Missing required FK fields!
    # This will still fail with IntegrityError
)
```

---

## PROPER FIX (90 MINUTES)

See: **PRODUCTION_DATA_LOADER_FIXES.md**

Key steps:
1. Add imports for PackagingType and PackagingMaterial
2. Create helper methods:
   - `_extract_packaging_info()`
   - `_get_or_create_packaging_type()`
   - `_get_or_create_packaging_material()`
   - `_get_or_create_packaging_color()`
3. Update `_load_pricing_entries()` to use helpers
4. Test with loader script
5. Verify all counts > 0

---

## DATA FILES STATUS

```
✅ EXIST - GeoJSON
├─ production_data/gps_layers/Exported 29 fields, 12 lines.geojson
│  └─ 8 warehouses + 8 storage areas + 12 storage locations
├─ production_data/gps_layers/naves.geojson (6286 lines)
├─ production_data/gps_layers/canteros.geojson (11894 lines)
└─ production_data/gps_layers/claros.geojson (49026 lines)

✅ EXIST - CSV
├─ production_data/product_category/categories.csv (13KB)
├─ production_data/product_category/categories_2.csv (78KB)
└─ production_data/price_list/price_list.csv (8.7KB)

STATUS: Data files are complete ✅
PROBLEM: Loader code has bugs ❌
SOLUTION: Fix loader code (90 min)
```

---

## ERROR CHAIN DIAGRAM

```
START: load_all_async()
   │
   ├─→ load_warehouses() 
   │    │
   │    ├─ Reads "Exported 29 fields, 12 lines.geojson"
   │    ├─ Parses 8 Warehouses (Nave 1-8)
   │    ├─ SHOULD ADD 8 records
   │    └─ ACTUALLY ADDS 0 (failure to log/update counter)
   │
   ├─→ load_storage_areas()
   │    │
   │    ├─ Needs: default_warehouse = first warehouse from DB
   │    │ RESULT: Gets None (because warehouses() returned 0)
   │    │
   │    └─ EARLY RETURN: "No warehouse found" → returns 0
   │
   ├─→ load_product_categories()
   │    │
   │    ├─ Reads categories.csv and categories_2.csv
   │    ├─ Creates ProductCategory records
   │    └─ Counter says 0 (idempotence - already exist)
   │
   ├─→ load_product_families()
   │    │
   │    ├─ Needs: ProductCategory records
   │    ├─ If product_categories=0 → families fail
   │    └─ CASCADING FAILURE
   │
   ├─→ load_products()
   │    │
   │    ├─ Needs: ProductFamily records
   │    ├─ If families=0 → products fail
   │    └─ CASCADING FAILURE
   │
   ├─→ load_storage_bin_types()
   │    │
   │    ├─ HARDCODED data (no file dependency)
   │    ├─ Creates 4 types: SEGMENTO, PLUGS, ALMACIGOS, CAJONES
   │    └─ Counter says 0 (idempotence - already exist)
   │
   ├─→ load_storage_location_config()
   │    │
   │    ├─ Needs: storage_locations (✅ exist) + products (❌ 0)
   │    ├─ Gets products → query returns None
   │    └─ EARLY RETURN: "No products found" → returns 0
   │
   └─→ load_price_list()
        │
        ├─ Reads price_list.csv
        ├─ Tries to create PackagingCatalog
        ├─ LINE 1549: PackagingCatalog.description ❌ ATTRIBUTE ERROR
        ├─ EXCEPTION CAUGHT (try-except around)
        └─ COUNTER SAYS 0 (no records added)

END: All counters = 0 (except storage_locations=12)
```

---

## FILES TO READ (IN ORDER)

1. **THIS FILE** (Quick Reference) - 5 min
2. **PRODUCTION_DATA_INVESTIGATION_SUMMARY.md** - 10 min
3. **PRODUCTION_DATA_LOADER_ANALYSIS.md** - 30 min (detailed)
4. **PRODUCTION_DATA_LOADER_FIXES.md** - 20 min (implementation)

---

## QUICK CHECKLIST

- [ ] Read Quick Reference (this file)
- [ ] Review Summary document
- [ ] Review Analysis document (detailed)
- [ ] Implement fixes from Fixes document
- [ ] Backup original file: `cp load_production_data.py load_production_data.py.backup`
- [ ] Make 5 changes (description→name, code→sku, add 3 helpers)
- [ ] Add imports (PackagingType, PackagingMaterial)
- [ ] Run test loader script
- [ ] Verify all counts > 0
- [ ] Commit changes

---

## LINE NUMBER REFERENCE

| Error | File | Lines | What |
|-------|------|-------|------|
| 1 | load_production_data.py | 1549 | `.description` → `.name` |
| 2 | load_production_data.py | 1557 | `code=` → `sku=` |
| 3 | load_production_data.py | 1558 | `description=` → `name=` |
| 4 | load_production_data.py | 1556-1562 | Add FK fields |
| 5 | load_production_data.py | 216-222 | Handle None warehouse |

