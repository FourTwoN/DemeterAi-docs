# Epic 004: Service Layer - Business Logic

**Status**: Ready
**Sprint**: Sprint-03 (Week 7-8)
**Priority**: high (core business logic)
**Total Story Points**: 210
**Total Cards**: 42 (S001-S042)

---

## Goal

Implement complete service layer with business logic, inter-service communication, validation rules,
and orchestration for all workflows (stock management, ML pipeline, configuration, analytics).

---

## Success Criteria

- [ ] All 42 services implemented following Clean Architecture
- [ ] Service→Service communication pattern enforced (NO direct repo access)
- [ ] Business validations implemented (ProductMismatchException, etc.)
- [ ] Manual initialization workflow complete
- [ ] Photo initialization workflow integrated with ML services
- [ ] All services have ≥80% test coverage
- [ ] Performance targets met (see individual cards)

---

## Cards List (42 cards, 210 points)

### Stock Management Services (30 points)

- **S001**: StockMovementService (8pts) - Core stock operations
- **S002**: StockBatchService (5pts) - Batch aggregation
- **S003**: ManualInitializationService (8pts) - Manual stock entry validation
- **S004**: ReconciliationService (5pts) - Monthly sales calculation
- **S005**: MovementTypeService (2pts) - Movement type validation
- **S006**: StockAggregationService (2pts) - Current stock calculation

### Location Services (20 points)

- **S007**: WarehouseService (3pts) - Warehouse CRUD
- **S008**: StorageAreaService (3pts) - Area CRUD
- **S009**: StorageLocationService (5pts) - Location CRUD + GPS lookup
- **S010**: StorageBinService (3pts) - Bin CRUD
- **S011**: LocationHierarchyService (3pts) - Tree traversal
- **S012**: GeospatialService (3pts) - PostGIS queries

### Product Services (15 points)

- **S013**: ProductService (3pts) - Product CRUD
- **S014**: ProductFamilyService (2pts) - Family CRUD
- **S015**: ProductCategoryService (2pts) - Category CRUD
- **S016**: ProductStateService (2pts) - State management
- **S017**: ProductSizeService (2pts) - Size management
- **S018**: ProductSearchService (4pts) - Full-text search

### Packaging & Pricing Services (12 points)

- **S019**: PackagingCatalogService (3pts) - Packaging CRUD
- **S020**: PackagingTypeService (2pts) - Type management
- **S021**: PriceListService (5pts) - Price calculation, bulk import
- **S022**: SKUGenerationService (2pts) - SKU auto-generation

### Photo & Image Services (25 points)

- **S023**: PhotoSessionService (8pts) - Session lifecycle
- **S024**: S3Service (8pts) - Upload/download with circuit breaker
- **S025**: ImageProcessingService (5pts) - Resize, compress, AVIF
- **S026**: EXIFExtractionService (2pts) - GPS, timestamp extraction
- **S027**: ThumbnailService (2pts) - 400×400 thumbnail generation

### Configuration Services (15 points)

- **S028**: StorageLocationConfigService (8pts) - Config validation
- **S029**: DensityParametersService (5pts) - Auto-calibration
- **S030**: ConfigValidationService (2pts) - Cross-validation

### ML Pipeline Services (60 points) - **CRITICAL PATH**

- **S031**: PipelineCoordinatorService (8pts) - Orchestrates full ML flow
- **S032**: LocalizationService (5pts) - GPS → storage_location
- **S033**: SegmentationService (8pts) - YOLO v11 segmentation
- **S034**: DetectionService (8pts) - YOLO v11 detection
- **S035**: SAHIDetectionService (8pts) - High-res sliced detection
- **S036**: BandEstimationService (8pts) - Band-based counting
- **S037**: DensityEstimationService (5pts) - Density-based counting
- **S038**: ClassificationService (5pts) - Product/packaging assignment
- **S039**: AggregationService (5pts) - Results aggregation

### Analytics Services (18 points)

- **S040**: ReportGenerationService (8pts) - Custom reports
- **S041**: DataExportService (5pts) - Excel/CSV export
- **S042**: ComparisonService (5pts) - Month-over-month comparison

---

## Dependencies

**Blocked By**: R001-R028 (repositories), DB001-DB035 (models)
**Blocks**: C001-C026 (controllers), CEL001-CEL008 (Celery tasks)

---

## Technical Approach

**Service Communication Pattern**:

```
✅ CORRECT:
ServiceA → ServiceB → RepoB
         ↓
      RepoA

❌ FORBIDDEN:
ServiceA → RepoB (must call ServiceB)
```

**Key Patterns**:

- Dependency injection via FastAPI `Depends()`
- Business exceptions (ProductMismatchException, etc.)
- Transaction management (Unit of Work)
- Circuit breaker for external services (S3Service)
- Model Singleton for ML models (load once per worker)

**Critical Validations**:

- Manual init: product_id must match storage_location_config
- Stock movements: quantity != 0, batch exists
- Photo upload: GPS within warehouse boundary
- ML pipeline: Config exists for location

---

**Epic Owner**: Backend Lead
**Created**: 2025-10-09
