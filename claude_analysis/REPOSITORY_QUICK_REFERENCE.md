# Repository Layer - Quick Reference Guide

**Last Updated**: 2025-10-21
**Status**: ✅ Production Ready
**Sprint**: Sprint 03

---

## Overview

| Aspect             | Value                        |
|--------------------|------------------------------|
| Total Repositories | 27 (26 specialized + 1 base) |
| Base Class         | AsyncRepository[T]           |
| Model Coverage     | 26/27 (96.3%)                |
| Inheritance        | 100% compliant               |
| Pattern Violations | 0                            |
| Audit Score        | A+ (95/100)                  |

---

## Base Repository Methods

All repositories inherit these CRUD methods from `AsyncRepository`:

```python
# Read
await repo.get(id)              # Get single record by ID
await repo.get_multi(skip=0, limit=100, **filters)  # Paginated list
await repo.count(**filters)     # Count records
await repo.exists(id)           # Check if exists

# Create
await repo.create(obj_in: dict) # Create new record

# Update
await repo.update(id, obj_in: dict)  # Update record

# Delete
await repo.delete(id)           # Delete record
```

---

## Repository List by Category

### ML Pipeline (4)

- `DetectionRepository` - Custom: `get_by_session`, `bulk_create`
- `EstimationRepository` - Custom: `get_by_session`, `get_by_calculation_method`, `bulk_create`
- `ClassificationRepository` - Base CRUD only
- `PhotoProcessingSessionRepository` - Custom: `get_by_session_id`, `get_by_storage_location`,
  `get_by_status`, `get_by_date_range`

### Warehouse Hierarchy (5)

- `WarehouseRepository` - Custom: `get_by_code`, `get_by_gps_point`, `get_active_warehouses`
- `StorageAreaRepository` - Base CRUD only
- `StorageLocationRepository` - Base CRUD only
- `StorageBinRepository` - Base CRUD only
- `StorageBinTypeRepository` - Base CRUD only

### Product Management (8)

- `ProductRepository` - Base CRUD only
- `ProductCategoryRepository` - Base CRUD only
- `ProductFamilyRepository` - Base CRUD only
- `ProductSizeRepository` - Base CRUD only
- `ProductStateRepository` - Base CRUD only
- `ProductSampleImageRepository` - Base CRUD only
- `S3ImageRepository` - Base CRUD only
- `PriceListRepository` - Base CRUD only

### Stock Management (2)

- `StockBatchRepository` - Base CRUD only
- `StockMovementRepository` - Base CRUD only

### Packaging (4)

- `PackagingTypeRepository` - Base CRUD only
- `PackagingColorRepository` - Base CRUD only
- `PackagingMaterialRepository` - Base CRUD only
- `PackagingCatalogRepository` - Base CRUD only

### Configuration (3)

- `StorageLocationConfigRepository` - Base CRUD only
- `DensityParameterRepository` - Base CRUD only
- `UserRepository` - Base CRUD only

---

## Common Usage Patterns

### Pattern 1: Get all records with pagination

```python
from app.repositories import ProductRepository

products = await product_repo.get_multi(skip=0, limit=50)
```

### Pattern 2: Filter records

```python
# Get active warehouses
warehouses = await warehouse_repo.get_multi(active=True)

# Get products by category
products = await product_repo.get_multi(product_category_id=5)
```

### Pattern 3: Create record

```python
new_product = await product_repo.create({
    "code": "PROD-001",
    "name": "Tomato Plant",
    "product_category_id": 1,
})
```

### Pattern 4: Update record

```python
updated = await product_repo.update(123, {
    "name": "Premium Tomato",
    "active": False
})
```

### Pattern 5: Delete record

```python
deleted = await product_repo.delete(123)  # Returns True/False
```

### Pattern 6: Custom query (when available)

```python
warehouse = await warehouse_repo.get_by_code("GH-001")
warehouse = await warehouse_repo.get_by_gps_point(-70.648, -33.449)
```

---

## Service Integration (Sprint 03)

### Correct Pattern

```python
from app.repositories import ProductRepository
from app.services import CategoryService

class ProductService:
    def __init__(
        self,
        repo: ProductRepository,  # Own repository
        category_service: CategoryService,  # Other services
    ):
        self.repo = repo
        self.category_service = category_service
```

### INCORRECT Pattern (DO NOT USE)

```python
class ProductService:
    def __init__(
        self,
        repo: ProductRepository,
        category_repo: CategoryRepository,  # WRONG! Use service instead
    ):
        self.category_repo = category_repo  # WRONG!
```

---

## File Locations

```
app/repositories/
├── base.py                           # AsyncRepository[T] base class
├── __init__.py
│
├── warehouse_repository.py           # Custom methods: 3
├── detection_repository.py           # Custom methods: 2
├── estimation_repository.py          # Custom methods: 3
├── photo_processing_session_repo.py  # Custom methods: 4
│
└── [22 other repositories]          # Base CRUD only
```

---

## Transaction Management

Repositories use `flush() + refresh()` pattern:

```python
# Create and get ID without committing
product = await repo.create(data)
# At this point:
# - product.id is populated
# - relationships are loaded
# - NOT committed to database yet

# Service/Endpoint is responsible for commit
await session.commit()  # Caller controls this
```

---

## Type Safety

All repositories use generics for type safety:

```python
class ProductRepository(AsyncRepository[Product]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Product, session)

    # Return type is always Product or list[Product]
    async def get(self, id: int) -> Product | None:
        ...
```

---

## Testing

### Unit Tests (Mock DB)

```bash
pytest tests/unit/repositories -v
```

### Integration Tests (Real DB)

```bash
pytest tests/integration/repositories -v
```

---

## Common Errors & Solutions

### Error: "Repository not found for model X"

**Solution**: Check if repository exists in `app/repositories/`

### Error: "Cannot import repository"

**Solution**: Verify import path:

```python
from app.repositories.product_repository import ProductRepository
# NOT: from app.repositories import ProductRepository.ProductRepository
```

### Error: "Method not found on repository"

**Solution**: Check if it's a custom method. If not, use base method:

```python
# WRONG if method_name is not custom
result = await repo.method_name()

# RIGHT
result = await repo.get(id)
result = await repo.get_multi(skip=0, limit=100)
```

---

## Performance Tips

1. **Use `with_areas=True` for eager loading** (WarehouseRepository)
   ```python
   warehouses = await repo.get_active_warehouses(with_areas=True)
   # Avoids N+1 queries
   ```

2. **Use `count()` for pagination metadata**
   ```python
   total = await repo.count()
   pages = (total + limit - 1) // limit
   ```

3. **Use `exists()` for presence check**
   ```python
   if await repo.exists(123):  # Faster than get()
       # Record exists
   ```

4. **Batch operations with `bulk_create()`** (DetectionRepository, EstimationRepository)
   ```python
   detections = await repo.bulk_create(detection_list)
   ```

---

## Related Documentation

- **Full Audit Report**: `/home/lucasg/proyectos/DemeterDocs/REPOSITORY_LAYER_AUDIT_REPORT.md`
- **Executive Summary**: `/home/lucasg/proyectos/DemeterDocs/REPOSITORY_AUDIT_EXECUTIVE_SUMMARY.txt`
- **Database Schema**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`
- **Architecture Guide**:
  `/home/lucasg/proyectos/DemeterDocs/engineering_plan/03_architecture_overview.md`

---

## Key Principles

1. **Repositories are data access only** - No business logic
2. **Services use repositories** - Not the other way around
3. **Services call services** - Not other repositories
4. **Transactions are caller-controlled** - Repositories don't commit
5. **All methods are async** - Use `async/await`
6. **Type hints required** - For all methods and parameters

---

## Audit Status

- **Overall Score**: A+ (95/100)
- **Production Ready**: ✅ YES
- **Blocking Issues**: ❌ NONE
- **Last Audit**: 2025-10-21

---

For detailed information, see the full audit report.
