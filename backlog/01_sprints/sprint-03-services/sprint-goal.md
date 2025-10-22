# Sprint 03: Services Layer

## Sprint Goal

**Duration**: Week 7-8 (Days 31-40)
**Team Capacity**: 80 story points
**Committed**: 76 story points

---

## Goal Statement

> **"Implement complete business logic layer (42 service classes) following Clean Architecture,
enabling API controller development in Sprint 04."**

---

## Success Criteria

- [ ] All location hierarchy services (Warehouse, Area, Location, Bin)
- [ ] All product/packaging services (Product, Family, Category, Packaging)
- [ ] Stock movement service (photo + manual initialization support)
- [ ] Stock batch service (event sourcing + aggregation)
- [ ] Photo session service (S3 integration, GPS localization)
- [ ] Configuration services (location config, density parameters)
- [ ] Service→Service communication pattern enforced (NO direct repo access)
- [ ] Unit tests ≥85% coverage for all services
- [ ] Integration tests with real database

---

## Sprint Scope

### In Scope (42 cards, 76 points)

**Location Services (S001-S010)**: 15 points

- Warehouse, StorageArea, StorageLocation, StorageBin services
- Geospatial queries (PostGIS integration)

**Product & Packaging Services (S011-S022)**: 18 points

- Product catalog management
- Packaging catalog management
- Classifications, pricing

**Stock Core Services (S023-S036)**: 25 points

- StockMovementService (CREATE: photo init, manual init, plantado, muerte, transplante, ventas)
- StockBatchService (aggregation, event sourcing)
- PhotoSessionService (S3 upload, processing coordination)

**Configuration Services (S037-S042)**: 18 points

- StorageLocationConfigService (expected product/packaging)
- DensityParameterService (auto-calibration)
- User management services

### Out of Scope

- ❌ API controllers (Sprint 04)
- ❌ Celery workers (Sprint 04)

---

## Key Deliverables

1. `app/services/location/` - 10 location services
2. `app/services/product/` - 12 product/packaging services
3. `app/services/stock/` - 14 stock management services
4. `app/services/config/` - 6 configuration services
5. Unit tests with ≥85% coverage

---

## Dependencies

**Blocked By**: Sprint 01 (Repositories), Sprint 02 (ML services)
**Blocks**: Sprint 04 (API controllers need services)

---

**Sprint Owner**: Backend Lead
**Last Updated**: 2025-10-09
