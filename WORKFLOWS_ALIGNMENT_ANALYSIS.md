# Workflows vs Implementation Alignment Analysis

**Date**: 2025-10-20
**Status**: Sprint 03 - Services Layer (42 tasks, 210 story points)
**Phase**: Complete workflow audit and gap analysis

---

## Executive Summary

This document provides a comprehensive analysis of all **38 Mermaid workflows** in the project against the **28 implemented services**.

**Key Findings**:
- **✅ Workflows Documented**: 38 comprehensive Mermaid diagrams
- **✅ Services Implemented**: 28 services (21 core + 7 ML-specific)
- **⚠️ Critical Gaps**: 12 services missing (circular implementation)
- **🔴 High-Risk Areas**: ML pipeline, stock transfers, export operations
- **📊 Implementation Status**: ~70% of workflow requirements covered

---

## 1. Workflows Inventory

### 1.1 ML Processing Workflows (10 files)

| Workflow | Scope | Steps | Status |
|----------|-------|-------|--------|
| `00_master_overview.mmd` | Complete pipeline overview | ~50 nodes | ✅ Documented |
| `01_complete_pipeline_v4.mmd` | Full implementation details | ~340 nodes | ✅ Documented |
| `02_api_entry_detailed.mmd` | API request handling | ~50 nodes | ⚠️ Partial impl |
| `03_s3_upload_circuit_breaker_detailed.mmd` | S3 with circuit breaker | ~80 nodes | 🔴 NOT IMPL |
| `04_ml_parent_segmentation_detailed.mmd` | YOLO segmentation | ~100 nodes | ⚠️ Partial impl |
| `05_sahi_detection_child_detailed.mmd` | SAHI detection child | ~120 nodes | ⚠️ Partial impl |
| `06_boxes_plugs_detection_detailed.mmd` | Direct detection child | ~60 nodes | ⚠️ Partial impl |
| `07_callback_aggregation_detailed.mmd` | Results aggregation | ~100 nodes | 🔴 NOT IMPL |
| `08_frontend_polling_detailed.mmd` | Frontend status polling | ~30 nodes | 🔴 NOT IMPL |

**Status**: 1/9 fully documented, 5/9 partially implemented, 3/9 not implemented

---

### 1.2 Stock Movements Workflows (1 file)

| Workflow | Operations | Steps | Status |
|----------|-----------|-------|--------|
| `trasplante_plantado_muerte.mmd` | Plantado, Transplante, Muerte | ~230 nodes | 🔴 CRITICAL GAP |

**Sub-operations**:
- **Plantado** (Plant/Initialize): ~50 nodes - ⚠️ Partial (manual only)
- **Transplante** (Transfer): ~80 nodes - 🔴 NOT IMPLEMENTED
- **Muerte** (Death/Remove): ~40 nodes - 🔴 NOT IMPLEMENTED

**Status**: Stock transfer operations NOT YET IMPLEMENTED

---

### 1.3 Manual Stock Initialization Workflow (1 file)

| Workflow | Scope | Steps | Status |
|----------|-------|-------|--------|
| `00_comprehensive_view.mmd` | Manual stock creation | ~20 nodes | ⚠️ Partial impl |

---

### 1.4 Storage Location Configuration (4 files)

| Workflow | Operation | Steps | Status |
|----------|-----------|-------|--------|
| `00_comprehensive_view.mmd` | Config overview | ~40 nodes | ✅ Documented |
| `01_update_existing_config.mmd` | UPDATE path | ~20 nodes | ✅ Implemented |
| `02_create_new_config.mmd` | CREATE path | ~25 nodes | ✅ Implemented |
| `03_frontend_configuration_view.mmd` | UI/UX view | - | Frontend only |

**Status**: Core logic implemented, frontend pending

---

### 1.5 Price List Management (5 files)

| Workflow | Operation | Steps | Status |
|----------|-----------|-------|--------|
| `00_comprehensive_view.mmd` | System overview | ~80 nodes | ✅ Documented |
| `01_packaging_catalog_crud.mmd` | Packaging CRUD | ~40 nodes | ✅ Services ready |
| `02_product_catalog_crud.mmd` | Product CRUD | ~50 nodes | ✅ Services ready |
| `03_price_list_management.mmd` | Price CRUD | ~40 nodes | ✅ Services ready |
| `04_bulk_edit_operations.mmd` | Bulk operations | ~60 nodes | 🔴 NOT IMPL |

**Status**: Individual CRUD complete, bulk operations not implemented

---

### 1.6 Analytics & Reporting (5 files)

| Workflow | Operation | Steps | Status |
|----------|-----------|-------|--------|
| `analiticas/00_comprehensive_view.mmd` | System overview | ~50 nodes | 📋 Controllers needed |
| `analiticas/01_manual_filters_query.mmd` | Manual filters | ~40 nodes | 📋 Controllers needed |
| `analiticas/02_sales_vs_stock_comparison.mmd` | Sales comparison | ~30 nodes | 📋 Controllers needed |
| `analiticas/03_ai_powered_analytics.mmd` | AI analytics | ~45 nodes | 📋 Controllers needed |
| `analiticas/04_data_export.mmd` | Export operations | ~35 nodes | 🔴 NOT IMPL |

**Status**: Services ready, controllers and export not implemented

---

### 1.7 Photo Upload Gallery (6 files)

| Workflow | Operation | Steps | Status |
|----------|-----------|-------|--------|
| `photo_upload_gallery/00_comprehensive_view.mmd` | System overview | ~60 nodes | 📋 Controllers needed |
| `photo_upload_gallery/01_photo_upload_initiation.mmd` | Upload start | ~20 nodes | 📋 Controllers needed |
| `photo_upload_gallery/02_job_monitoring_progress.mmd` | Job monitoring | ~25 nodes | 📋 Controllers needed |
| `photo_upload_gallery/03_photo_gallery_view.mmd` | Gallery display | ~30 nodes | 📋 Controllers needed |
| `photo_upload_gallery/04_error_recovery_reprocessing.mmd` | Error handling | ~35 nodes | 📋 Controllers needed |
| `photo_upload_gallery/05_photo_detail_display.mmd` | Detail view | ~20 nodes | 📋 Controllers needed |

**Status**: Services ready, controllers needed for frontend integration

---

### 1.8 Warehouse Map Views (6 files)

| Workflow | Operation | Steps | Status |
|----------|-----------|-------|--------|
| `map_warehouse_views/00_comprehensive_view.mmd` | System overview | ~50 nodes | 📋 Controllers needed |
| `map_warehouse_views/01_warehouse_map_overview.mmd` | Warehouse map | ~40 nodes | 📋 Controllers needed |
| `map_warehouse_views/02_warehouse_internal_structure.mmd` | Internal structure | ~30 nodes | 📋 Controllers needed |
| `map_warehouse_views/03_storage_location_preview.mmd` | Location preview | ~25 nodes | 📋 Controllers needed |
| `map_warehouse_views/04_storage_location_detail.mmd` | Detail view | ~35 nodes | 📋 Controllers needed |
| `map_warehouse_views/05_historical_timeline.mmd` | Historical data | ~40 nodes | 📋 Controllers needed |

**Status**: Services ready, visualization controllers needed

---

## 2. Services Implementation Status

### 2.1 Core Services (21 files)

| Service | Purpose | Status | Methods | Missing |
|---------|---------|--------|---------|---------|
| `warehouse_service.py` | Warehouse hierarchy | ✅ Complete | CRUD | - |
| `storage_area_service.py` | Storage areas | ✅ Complete | CRUD | - |
| `storage_location_service.py` | Storage locations | ✅ Complete | CRUD, geoquery | - |
| `storage_location_config_service.py` | Location configs | ✅ Complete | CRUD | History tracking |
| `storage_bin_service.py` | Storage bins | ✅ Complete | CRUD | - |
| `storage_bin_type_service.py` | Bin types | ✅ Complete | CRUD | - |
| `product_category_service.py` | Product categories | ✅ Complete | CRUD | - |
| `product_family_service.py` | Product families | ✅ Complete | CRUD | - |
| `product_size_service.py` | Product sizes | ✅ Complete | CRUD | - |
| `product_state_service.py` | Product states | ✅ Complete | CRUD | - |
| `packaging_catalog_service.py` | Packaging catalog | ✅ Complete | CRUD | - |
| `packaging_type_service.py` | Packaging types | ✅ Complete | CRUD | - |
| `packaging_color_service.py` | Packaging colors | ✅ Complete | CRUD | - |
| `packaging_material_service.py` | Packaging materials | ✅ Complete | CRUD | - |
| `price_list_service.py` | Price management | ✅ Complete | CRUD | Bulk operations |
| `stock_batch_service.py` | Stock batches | ⚠️ Minimal | Create, get, update_qty | Lifecycle methods |
| `stock_movement_service.py` | Movement audit | ⚠️ Minimal | Create, get_by_batch | Transfer operations |
| `batch_lifecycle_service.py` | Batch lifecycle | ✅ Complete | Activate, deactivate | - |
| `movement_validation_service.py` | Movement validation | ⚠️ Minimal | Basic validation | Complex rules |
| `density_parameter_service.py` | Density params | ✅ Complete | CRUD | Auto-calibration |
| `location_hierarchy_service.py` | Hierarchy ops | ✅ Complete | Get tree, validate | - |

**Analysis**:
- **✅ 14 services**: Complete CRUD + domain logic
- **⚠️ 7 services**: Minimal implementation, need enhancement
- **🔴 0 services**: Not started (already have stubs)

---

### 2.2 ML Processing Services (7 files)

| Service | Purpose | Status | Methods | Missing |
|---------|---------|--------|---------|---------|
| `model_cache.py` | Model singleton cache | ✅ Complete | Load, get | - |
| `segmentation_service.py` | YOLO segmentation | ✅ Complete | Segment image | - |
| `sahi_detection_service.py` | SAHI detection | ✅ Complete | Detect in segment | Classification link |
| `band_estimation_service.py` | Band estimation | ✅ Complete | Estimate undetected | Auto-calibration |
| `pipeline_coordinator.py` | Pipeline orchestration | ✅ Complete | Process complete | Callback trigger |

**Analysis**:
- **✅ 5 services**: Core ML pipeline complete
- **⚠️ Missing integrations**:
  - Callback aggregation
  - Classification service integration
  - Stock batch creation from ML results

---

## 3. Critical Gaps Analysis

### 3.1 ML Pipeline Gaps

#### Gap 1: S3 Upload with Circuit Breaker (CRITICAL)
**Location**: Workflow `03_s3_upload_circuit_breaker_detailed.mmd`
**Impact**: Photo upload will fail if S3 is down; no resilience
**Required**:
- `S3UploadService` (new)
  - `upload_batch(uuids: List[str]) → Summary`
  - Circuit breaker state management
  - Thumbnail generation (AVIF)
  - EXIF metadata extraction
- `ExifExtractionService` (new)
  - Extract GPS, timestamp, camera info
- `CircuitBreakerManager` (new)
  - State: OPEN, HALF_OPEN, CLOSED
  - Threshold: 50% failure rate
  - Timeout: 60s recovery

**Estimation**: 3-4 tasks (1-2 days)

---

#### Gap 2: Callback Aggregation (CRITICAL)
**Location**: Workflow `07_callback_aggregation_detailed.mmd`
**Impact**: ML results cannot be aggregated into stock batches; pipeline fails
**Required**:
- `AggregationService` (new)
  - `aggregate_results(results: List[dict]) → AggregateResult`
  - Weighted average confidence
  - Total counts calculation
- `VisualizationService` (new)
  - Draw detections (circles)
  - Draw estimations (masks)
  - Add legend and text
- `VisualizationCompressionService` (new)
  - AVIF compression (quality=85)
  - Thumbnail generation
- Enhanced `StockBatchService`
  - `create_from_ml_results(movements, classifications)`
  - Auto-generate batch_code with date/sequence
  - Comprehensive verification with rollback

**Estimation**: 4-5 tasks (2 days)

---

#### Gap 3: Classification Service (HIGH PRIORITY)
**Location**: Workflows `05_sahi_detection_child_detailed.mmd`, `06_boxes_plugs_detection_detailed.mmd`
**Impact**: Cannot link detections to product/packaging classification
**Required**:
- `ClassificationService` (new)
  - `get_or_create(product_id, packaging_id, model_version)`
  - Store metadata about the ML model used
  - Support querying detections by classification

**Estimation**: 1-2 tasks (4-8 hours)

---

#### Gap 4: Geolocation Service (MEDIUM PRIORITY)
**Location**: Workflow `04_ml_parent_segmentation_detailed.mmd`
**Impact**: Cannot geolocate photos; manual location assignment required
**Required**:
- `GeolocationService` (new)
  - `get_location_from_gps(lat, lon) → StorageLocation`
  - Uses PostGIS ST_Contains for spatial queries
  - Handles warning state if location not found

**Estimation**: 1 task (4 hours)

---

### 3.2 Stock Movement Gaps

#### Gap 5: Transfer Service (CRITICAL - BLOCKING)
**Location**: Workflow `trasplante_plantado_muerte.mmd` - Transplante operation
**Impact**: Cannot transfer stock between locations; core business operation blocked
**Required**:
- `TransferService` (new)
  - `transplant_stock(source_loc, dest_loc, product, quantity) → TransferResult`
  - Two-phase transaction: OUT from source, IN to destination
  - Atomic all-or-nothing
  - Auto-create bins if needed
  - Auto-create/find batches
  - Comprehensive verification
  - Deactivate source batch if quantity=0

**Estimation**: 3-4 tasks (1.5 days)

---

#### Gap 6: Death/Removal Service (MEDIUM)
**Location**: Workflow `trasplante_plantado_muerte.mmd` - Muerte operation
**Impact**: Cannot record plant death; inventory tracking incomplete
**Required**:
- `DeathService` (new)
  - `record_death(location_id, product, quantity) → DeathResult`
  - Track dead vs live separately
  - Update quantity_empty_containers in batch
  - Deactivate batch if all dead
  - Audit trail with reason

**Estimation**: 2 tasks (1 day)

---

### 3.3 Export & Analytics Gaps

#### Gap 7: Bulk Operations Service (MEDIUM)
**Location**: Workflow `04_bulk_edit_operations.mmd`
**Impact**: Cannot perform bulk price updates; admin operation blocked
**Required**:
- `BulkOperationService` (new)
  - `bulk_update_prices(filter, operation, value)`
  - `bulk_update_availability(filter, status)`
  - `bulk_apply_discount(filter, percentage)`
  - Transaction-wrapped
  - Audit logging

**Estimation**: 2 tasks (1 day)

---

#### Gap 8: Export Service (MEDIUM)
**Location**: Workflows `analiticas/04_data_export.mmd`, `photo_upload_gallery/`
**Impact**: Cannot export reports; business reporting blocked
**Required**:
- `ExportService` (new)
  - `export_to_excel(data, format)`
  - `export_to_csv(data)`
  - `export_to_pdf(data, template)`
  - Templating for different report types

**Estimation**: 3 tasks (1.5 days)

---

### 3.4 Enhancement Gaps

#### Gap 9: StockMovementService Enhancements (HIGH)
**Current**: Only create + get_by_batch
**Needed**:
- `validate_movement(movement)` → Validation result
- `link_to_batch(movement, batch)`
- `get_by_session(session_id)` → List of movements
- Comprehensive audit trail methods

**Estimation**: 1 task (4 hours)

---

#### Gap 10: StockBatchService Enhancements (HIGH)
**Current**: Only create + get + update_qty
**Needed**:
- `find_or_create(location_id, product_id, packaging_id)`
- `deactivate(batch_id)` → Mark as inactive
- `get_by_location(location_id)` → Active batches
- `verify_data_integrity(batch_id)` → Boolean
- Lifecycle management methods

**Estimation**: 1 task (4 hours)

---

#### Gap 11: StorageLocationConfigService Enhancements (MEDIUM)
**Current**: Basic CRUD
**Needed**:
- `deactivate(id)` → Atomic deactivation
- `create_new_version(id, new_data)` → With history
- `get_active_for_location(location_id)`
- History tracking and audit

**Estimation**: 1 task (4 hours)

---

#### Gap 12: MovementValidationService Enhancements (MEDIUM)
**Current**: Minimal validation
**Needed**:
- Complex business rule validation
- Sufficient quantity checks
- Cross-location validation
- State transition validation

**Estimation**: 1 task (4 hours)

---

## 4. Alignment Matrix

### 4.1 Workflow Completion Status

```
CRITICAL WORKFLOWS (Blocking progress):
├─ ML Pipeline (Master + Complete)
│  ├─ API Entry: ⚠️ 70% (S3 service missing)
│  ├─ S3 Upload: 🔴 0% (Circuit breaker missing)
│  ├─ ML Parent: ⚠️ 80% (Geolocation missing)
│  ├─ SAHI Child: ⚠️ 85% (Classification missing)
│  ├─ Boxes Child: ⚠️ 85% (Classification missing)
│  └─ Callback: 🔴 10% (Aggregation service missing)
│
├─ Stock Movements
│  ├─ Plantado: ⚠️ 50% (Minimal service)
│  ├─ Transplante: 🔴 0% (Transfer service missing)
│  └─ Muerte: 🔴 0% (Death service missing)
│
└─ Other
   ├─ Manual Stock Init: ⚠️ 60%
   ├─ Location Config: ✅ 95%
   └─ Price List: ⚠️ 70% (Bulk ops missing)

NON-CRITICAL (Controllers needed only):
├─ Analytics: ✅ Services ready
├─ Photo Gallery: ✅ Services ready
├─ Warehouse Maps: ✅ Services ready
└─ Export: 🔴 Missing export service
```

---

### 4.2 Services Status Summary

```
COMPLETE & READY (14 services):
✅ Warehouse, StorageArea, StorageLocation, StorageBin, StorageBinType
✅ ProductCategory, ProductFamily, ProductSize, ProductState
✅ PackagingCatalog, PackagingType, PackagingColor, PackagingMaterial
✅ PriceList, BatchLifecycle, DensityParameter, LocationHierarchy
✅ ML Pipeline: ModelCache, SegmentationService, SAHIDetectionService
✅ ML Pipeline: BandEstimationService, MLPipelineCoordinator

PARTIAL/MINIMAL (7 services):
⚠️ StockBatchService: Only basic CRUD
⚠️ StockMovementService: Only basic CRUD + one query
⚠️ MovementValidationService: Minimal validation
⚠️ StorageLocationConfigService: Basic CRUD (needs deactivation logic)
⚠️ SAHIDetectionService: Needs classification linking
⚠️ BandEstimationService: Needs auto-calibration integration
⚠️ Pipeline Coordinator: Needs callback integration

NOT IMPLEMENTED (12 services):
🔴 S3UploadService
🔴 ExifExtractionService
🔴 CircuitBreakerManager
🔴 GeolocationService
🔴 ClassificationService
🔴 AggregationService
🔴 VisualizationService
🔴 VisualizationCompressionService
🔴 TransferService
🔴 DeathService
🔴 BulkOperationService
🔴 ExportService
```

---

## 5. Implementation Priority & Roadmap

### Phase 1: CRITICAL - ML Pipeline Completion (Days 1-2)

**Must complete for photo processing to work**:

1. **S3UploadService** (8 hours)
   - Circuit breaker pattern
   - EXIF extraction
   - Thumbnail generation
   - Status tracking

2. **ClassificationService** (4 hours)
   - Get or create logic
   - Link to detections
   - Model versioning

3. **AggregationService** (8 hours)
   - Aggregate totals
   - Weighted confidence
   - Visualization generation
   - Batch creation

4. **GeolocationService** (4 hours)
   - PostGIS queries
   - Warning state handling

**Subtasks**: 4 services, ~6 tasks, 1.5 days

---

### Phase 2: HIGH - Stock Operations (Days 3-4)

**Must complete for inventory management**:

1. **TransferService** (8 hours)
   - Two-phase transaction
   - Auto bin/batch creation
   - Verification & rollback

2. **DeathService** (4 hours)
   - Death recording
   - Empty container tracking

3. **Enhance StockBatchService** (4 hours)
   - Lifecycle methods
   - Find or create logic

4. **Enhance StockMovementService** (4 hours)
   - Validation methods
   - Batch linking

**Subtasks**: 4 services, 4 tasks, 1 day

---

### Phase 3: MEDIUM - Export & Admin (Days 5-6)

**Nice-to-have business operations**:

1. **BulkOperationService** (4 hours)
   - Bulk price updates
   - Bulk availability changes

2. **ExportService** (8 hours)
   - Excel/CSV/PDF export
   - Templating

3. **Enhance StorageLocationConfigService** (4 hours)
   - Deactivation logic
   - Version history

**Subtasks**: 3 services, 3 tasks, 1 day

---

## 6. Quality Gate Validations

### 6.1 ML Pipeline Verification

```
Before marking workflow complete:

✅ S3Upload:
   - [ ] Circuit breaker state transitions work
   - [ ] EXIF extraction successful
   - [ ] Thumbnail AVIF compression 50% smaller than JPEG
   - [ ] Database updates reflect correct status
   - [ ] Test with S3 failure scenario

✅ Classification:
   - [ ] get_or_create is idempotent
   - [ ] Detections link correctly to classification
   - [ ] Query by classification returns correct results

✅ Aggregation:
   - [ ] Totals calculated correctly
   - [ ] Weighted confidence within 0.0-1.0
   - [ ] Visualization renders detections + estimations
   - [ ] Batch codes are unique per location-date
   - [ ] Rollback works on verification failure
   - [ ] All 4 stages complete: Segment→Detect→Estimate→Aggregate

✅ Geolocation:
   - [ ] PostGIS queries return correct location
   - [ ] GPS missing creates warning session
   - [ ] Outside area creates warning session
```

---

### 6.2 Stock Operations Verification

```
Before marking workflow complete:

✅ Transfer:
   - [ ] Source batch decremented correctly
   - [ ] Destination batch created or incremented
   - [ ] Both movements linked to batches
   - [ ] Transaction atomic (all-or-nothing)
   - [ ] Deactivation when quantity=0
   - [ ] Test with insufficient stock scenario
   - [ ] Test with same-location rejection

✅ Death:
   - [ ] Quantity decremented from current
   - [ ] Quantity incremented in empty_containers
   - [ ] Sum(current + empty) = original
   - [ ] Batch deactivated when all dead
   - [ ] Audit trail shows death reason
```

---

## 7. Risk Assessment

### High Risk

| Risk | Impact | Mitigation |
|------|--------|-----------|
| S3 circuit breaker not working | Photos fail to upload | Implement robust pattern, extensive testing |
| ML callback aggregation incomplete | Results lost, pipeline hangs | Schema validation + transaction safety |
| Transfer service race conditions | Stock counts corrupt | Use database locks, comprehensive verification |
| Geolocation fails silently | Wrong counts assigned to wrong locations | Warning states, manual override |

---

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Classification service not robust | Detections not linked | Unit tests for idempotency |
| Visualization generation slow | Callback takes >5 min | Async task, progress tracking |
| Export service too complex | Export doesn't work | Start simple (CSV), add formats later |

---

## 8. Recommendations

### For Sprint 03 Completion

**Priority 1 (MUST HAVE)**:
- [x] All 14 base CRUD services (already done)
- [x] ML pipeline services (segmentation, SAHI, band estimation) (already done)
- [ ] S3UploadService with circuit breaker
- [ ] ClassificationService
- [ ] AggregationService
- [ ] GeolocationService
- [ ] TransferService
- [ ] StockBatchService enhancements
- [ ] StockMovementService enhancements

**Priority 2 (SHOULD HAVE)**:
- [ ] DeathService
- [ ] Enhance StorageLocationConfigService
- [ ] Enhance MovementValidationService
- [ ] BulkOperationService

**Priority 3 (NICE TO HAVE)**:
- [ ] ExportService
- [ ] Analytics controllers
- [ ] Visualization controllers

---

### For Production Readiness

1. **Test all 12 missing services** with real Celery workers
2. **Load test** ML pipeline with 100+ concurrent photos
3. **Verify database integrity** after transfers/deaths
4. **Monitor S3 circuit breaker** behavior in staging
5. **Audit trail** for all stock movements
6. **Backup/restore** testing for critical operations

---

## 9. File Structure for New Services

```
app/services/
├── s3_upload_service.py          (NEW - 200 lines)
├── exif_extraction_service.py    (NEW - 100 lines)
├── circuit_breaker_manager.py    (NEW - 150 lines)
├── geolocation_service.py        (NEW - 100 lines)
├── classification_service.py     (NEW - 100 lines)
├── aggregation_service.py        (NEW - 200 lines)
├── visualization_service.py      (NEW - 250 lines)
├── transfer_service.py           (NEW - 300 lines)
├── death_service.py              (NEW - 150 lines)
├── bulk_operation_service.py     (NEW - 200 lines)
├── export_service.py             (NEW - 300 lines)
├── ml_processing/
│   ├── pipeline_coordinator.py   (✅ EXISTS)
│   ├── segmentation_service.py   (✅ EXISTS)
│   ├── sahi_detection_service.py (✅ EXISTS)
│   ├── band_estimation_service.py (✅ EXISTS)
│   └── model_cache.py            (✅ EXISTS)
└── [14 existing CRUD services]
```

---

## 10. Appendix: Detailed Service Mapping

### ML Pipeline Workflow → Services

```
API Entry
├─ StockMovementService.create_stock_movement()
├─ S3UploadService.upload_batch() [NEW]
└─ Celery task dispatch

S3 Upload
├─ ExifExtractionService.extract() [NEW]
├─ S3UploadService.upload_with_retry() [NEW]
├─ CircuitBreakerManager [NEW]
└─ S3ImagesRepository.update()

ML Parent - Segmentation
├─ ModelCache.get_worker_model()
├─ SegmentationService.segment_image()
├─ ExifExtractionService.extract()
├─ GeolocationService.get_location_from_gps() [NEW]
├─ StorageLocationConfigService.get_by_location()
├─ DensityParameterService.get()
└─ PhotoProcessingSessionRepository.create_warning()

SAHI Child Detection
├─ SAHIDetectionService.detect_in_segmento()
├─ ClassificationService.get_or_create() [NEW]
├─ StockMovementService.create_stock_movement()
├─ DetectionRepository.bulk_insert()
├─ BandEstimationService.estimate_undetected_plants()
├─ DensityParameterService.update() [auto-calibration]
└─ EstimationRepository.bulk_insert()

Boxes Child Detection
├─ (Same as SAHI, but direct YOLO)

Callback Aggregation
├─ AggregationService.aggregate_results() [NEW]
├─ VisualizationService.draw_detections() [NEW]
├─ VisualizationService.draw_estimations() [NEW]
├─ S3UploadService.upload_viz() [NEW]
├─ StockBatchService.create_from_ml_results() [NEW]
├─ StockMovementService.link_to_batch() [NEW]
├─ PhotoProcessingSessionRepository.update()
└─ TransactionManager.commit()
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-20
**Maintained By**: DemeterAI Engineering Team
