# Service→Service Pattern - Quick Reference Card
**DemeterAI v2.0 Clean Architecture**

---

## ✅ CORRECT Pattern (Use This!)

```python
# ✅ CORRECT: Service depends on OTHER SERVICES
class ProductService:
    def __init__(
        self,
        product_repo: ProductRepository,          # ✅ Own repository
        category_service: ProductCategoryService, # ✅ Service dependency
        family_service: ProductFamilyService      # ✅ Service dependency
    ):
        self.product_repo = product_repo
        self.category_service = category_service  # ✅ CORRECT
        self.family_service = family_service      # ✅ CORRECT

    async def create_product(self, request: CreateProductRequest):
        # Validate category via CategoryService
        category = await self.category_service.get_by_id(request.category_id)  # ✅

        # Validate family via FamilyService
        family = await self.family_service.get_by_id(request.family_id)  # ✅

        # Create via own repository
        product = await self.product_repo.create(request.model_dump())  # ✅

        return ProductResponse.from_model(product)
```

---

## ❌ WRONG Pattern (Never Do This!)

```python
# ❌ WRONG: Service depends on OTHER REPOSITORIES
class BAD_ProductService:
    def __init__(
        self,
        product_repo: ProductRepository,
        category_repo: ProductCategoryRepository,  # ❌ VIOLATION!
        family_repo: ProductFamilyRepository       # ❌ VIOLATION!
    ):
        self.product_repo = product_repo
        self.category_repo = category_repo  # ❌ WRONG
        self.family_repo = family_repo      # ❌ WRONG

    async def create_product(self, request):
        # ❌ WRONG: Direct repository access bypasses business logic
        category = await self.category_repo.get(request.category_id)
        family = await self.family_repo.get(request.family_id)

        # ❌ Missing validation, error handling, business rules
        product = await self.product_repo.create(request.model_dump())
        return product
```

**Why This Is Wrong**:
1. Bypasses business logic in CategoryService/FamilyService
2. Bypasses validation rules
3. Bypasses error handling
4. Violates Clean Architecture (Service layer calls Repository layer of OTHER domains)
5. Makes testing harder (must mock repositories instead of services)

---

## Pattern Decision Tree

```
Need to access data from another domain?
    │
    ├─ Is it MY OWN data (my model)?
    │   └─ ✅ Use self.repo (own repository)
    │
    └─ Is it ANOTHER domain's data?
        ├─ ❌ NEVER use other_repo (repository)
        └─ ✅ ALWAYS use other_service (service)
```

---

## Real Examples from DemeterAI

### Example 1: Warehouse Hierarchy

```python
# ✅ CORRECT: StorageAreaService validates parent warehouse via WarehouseService
class StorageAreaService:
    def __init__(
        self,
        storage_area_repo: StorageAreaRepository,  # ✅ Own repo
        warehouse_service: WarehouseService        # ✅ Service (NOT warehouse_repo)
    ):
        self.storage_area_repo = storage_area_repo
        self.warehouse_service = warehouse_service

    async def create_storage_area(self, request):
        # Validate parent warehouse exists
        warehouse = await self.warehouse_service.get_warehouse_by_id(
            request.warehouse_id
        )  # ✅ Service call

        # Validate geometry containment
        self._validate_within_parent(
            request.geojson_coordinates,
            warehouse.geojson_coordinates
        )

        # Create via own repository
        area = await self.storage_area_repo.create(request.model_dump())  # ✅
        return StorageAreaResponse.from_model(area)
```

### Example 2: Product Taxonomy

```python
# ✅ CORRECT: ProductFamilyService validates category via ProductCategoryService
class ProductFamilyService:
    def __init__(
        self,
        family_repo: ProductFamilyRepository,     # ✅ Own repo
        category_service: ProductCategoryService  # ✅ Service (NOT category_repo)
    ):
        self.family_repo = family_repo
        self.category_service = category_service

    async def create_family(self, request):
        # Validate parent category exists
        await self.category_service.get_category_by_id(request.category_id)  # ✅

        # Create via own repository
        family = await self.family_repo.create(request.model_dump())  # ✅
        return ProductFamilyResponse.from_model(family)
```

### Example 3: GPS Localization Chain

```python
# ✅ CORRECT: StorageLocationService chains 3 services for GPS lookup
class StorageLocationService:
    def __init__(
        self,
        location_repo: StorageLocationRepository,  # ✅ Own repo
        warehouse_service: WarehouseService,       # ✅ Service
        area_service: StorageAreaService           # ✅ Service
    ):
        self.location_repo = location_repo
        self.warehouse_service = warehouse_service
        self.area_service = area_service
        # NO warehouse_repo ✅
        # NO area_repo ✅

    async def get_location_by_gps(self, longitude: float, latitude: float):
        # Step 1: Find warehouse via WarehouseService
        warehouse = await self.warehouse_service.get_warehouse_by_gps(
            longitude, latitude
        )  # ✅
        if not warehouse:
            return None

        # Step 2: Find area via StorageAreaService
        area = await self.area_service.get_storage_area_by_gps(
            longitude, latitude, warehouse_id=warehouse.warehouse_id
        )  # ✅
        if not area:
            return None

        # Step 3: Find location via own repository
        location = await self.location_repo.find_by_gps(longitude, latitude)  # ✅
        return StorageLocationResponse.from_model(location)
```

---

## Aggregator Pattern (No Repositories)

```python
# ✅ CORRECT: Aggregator service has ZERO repositories
class LocationHierarchyService:
    def __init__(
        self,
        warehouse_service: WarehouseService,      # ✅ Service
        area_service: StorageAreaService,         # ✅ Service
        location_service: StorageLocationService, # ✅ Service
        bin_service: StorageBinService           # ✅ Service
    ):
        # NO REPOSITORIES AT ALL ✅
        self.warehouse_service = warehouse_service
        self.area_service = area_service
        self.location_service = location_service
        self.bin_service = bin_service

    async def get_full_hierarchy(self, warehouse_id: int):
        # All operations via services
        warehouse = await self.warehouse_service.get_warehouse_by_id(warehouse_id)  # ✅
        areas = await self.area_service.get_areas_by_warehouse(warehouse_id)        # ✅

        for area in areas:
            locations = await self.location_service.get_locations_by_area(
                area.storage_area_id
            )  # ✅

            for loc in locations:
                bins = await self.bin_service.get_bins_by_location(
                    loc.storage_location_id
                )  # ✅
```

---

## Common Mistakes & Fixes

### Mistake 1: Injecting Repository Instead of Service

```python
# ❌ WRONG
class StockMovementService:
    def __init__(
        self,
        movement_repo: StockMovementRepository,
        batch_repo: StockBatchRepository  # ❌ Should be batch_service
    ):
        ...

# ✅ CORRECT
class StockMovementService:
    def __init__(
        self,
        movement_repo: StockMovementRepository,
        batch_service: StockBatchService  # ✅ Service
    ):
        ...
```

### Mistake 2: Bypassing Business Logic

```python
# ❌ WRONG
async def create_product(self, request):
    # Bypasses validation in CategoryService
    category = await self.category_repo.get(request.category_id)  # ❌
    if not category:
        raise ValueError("Not found")  # ❌ Wrong exception type

# ✅ CORRECT
async def create_product(self, request):
    # Uses CategoryService (includes validation, proper exceptions)
    category = await self.category_service.get_by_id(request.category_id)  # ✅
    # Raises ProductCategoryNotFoundException if not found ✅
```

### Mistake 3: Missing Service Dependencies

```python
# ❌ WRONG: PackagingCatalogService doesn't validate FKs
class PackagingCatalogService:
    def __init__(self, repo: PackagingCatalogRepository):
        self.repo = repo

    async def create(self, request):
        # ❌ No validation of packaging_type_id, color_id, material_id
        return await self.repo.create(request.model_dump())

# ✅ CORRECT: Validate all FKs via services
class PackagingCatalogService:
    def __init__(
        self,
        repo: PackagingCatalogRepository,
        type_service: PackagingTypeService,      # ✅
        color_service: PackagingColorService,    # ✅
        material_service: PackagingMaterialService  # ✅
    ):
        self.repo = repo
        self.type_service = type_service
        self.color_service = color_service
        self.material_service = material_service

    async def create(self, request):
        # Validate all FKs
        await self.type_service.get_by_id(request.packaging_type_id)      # ✅
        await self.color_service.get_by_id(request.packaging_color_id)    # ✅
        await self.material_service.get_by_id(request.packaging_material_id)  # ✅

        return await self.repo.create(request.model_dump())
```

---

## Checklist for New Services

When creating a new service, verify:

- [ ] `__init__` only injects OWN repository (e.g., `ProductRepository` for `ProductService`)
- [ ] `__init__` injects OTHER SERVICES (not repositories) for cross-domain operations
- [ ] All `__init__` parameters have type hints
- [ ] All public methods are `async def`
- [ ] All public methods have type hints (args + return type)
- [ ] All public methods have docstrings (Args, Returns, Raises)
- [ ] Business validation uses services (not direct repository access)
- [ ] Custom exceptions used (not generic `ValueError`)
- [ ] Pydantic schemas returned (not SQLAlchemy models)

---

## Testing Service→Service Pattern

```python
# ✅ CORRECT: Mock services (not repositories)
@pytest.mark.asyncio
async def test_create_product(mock_category_service, mock_family_service):
    # Setup mocks
    mock_category_service.get_by_id = AsyncMock(return_value=category_response)
    mock_family_service.get_by_id = AsyncMock(return_value=family_response)

    # Create service with mocked services
    service = ProductService(
        product_repo=product_repo,
        category_service=mock_category_service,  # ✅ Service
        family_service=mock_family_service       # ✅ Service
    )

    # Act
    result = await service.create_product(request)

    # Assert
    mock_category_service.get_by_id.assert_called_once()  # ✅
    mock_family_service.get_by_id.assert_called_once()    # ✅
```

---

## Key Principles

1. **Service→Service**: Services call OTHER services (not repositories)
2. **Own Repository**: Services only access THEIR OWN repository
3. **Business Logic**: Services contain business logic (repositories contain CRUD)
4. **Dependency Injection**: All dependencies injected via `__init__`
5. **Type Safety**: Type hints on all methods
6. **Async First**: All database operations async
7. **Custom Exceptions**: Domain errors use custom exceptions
8. **Pydantic Schemas**: Return schemas (not models)

---

## References

- **Detailed Audit**: `SERVICE_ARCHITECTURE_AUDIT_REPORT.md`
- **Violations Summary**: `SERVICE_VIOLATIONS_SUMMARY.md`
- **Python Expert Workflow**: `.claude/workflows/python-expert-workflow.md`
- **Template**: `backlog/04_templates/starter-code/base_service.py`

---

**Last Updated**: 2025-10-20
**Status**: All 21 services compliant ✅
