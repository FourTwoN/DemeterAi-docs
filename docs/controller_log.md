# Controller Work Log

Date: 2025-10-27

## Photo Controller (`app/controllers/photo_controller.py`)
- Added gallery endpoint `GET /api/v1/photos/gallery` with filtering and pagination.
- Implemented photo detail endpoint `GET /api/v1/photos/{image_id}` returning metadata, session summary, history.
- Added job status polling endpoint `GET /api/v1/photos/jobs/status` backed by Redis via `PhotoJobService`.
- Exposed reprocess endpoint `POST /api/v1/photos/{image_id}/reprocess` (uses ML Celery task) and batch delete endpoint `POST /api/v1/photos/batch-delete` (soft delete).
- Added session progress, validation, and export endpoints (`GET /sessions/{id}/progress`, `POST /sessions/{id}/validate`, downloads for PDF/CSV/GeoJSON).
- Services used: `PhotoQueryService`, `PhotoJobService`, `PhotoProcessingSessionService`, `S3ImageService`.

## Map Controller (`app/controllers/map_controller.py`)
- New endpoints for map visualizations:
  - `GET /api/v1/map/bulk-load` returns warehouses, areas, and location previews.
  - `GET /api/v1/storage-locations/{id}/detail` basic location detail view.
  - `GET /api/v1/storage-locations/{id}/history` returns recent history timeline.
- Powered by `MapViewService` which aggregates data from warehouse/location/session services.

## Admin Controller (`app/controllers/admin_controller.py`)
- Introduced admin hierarchy endpoint `GET /api/admin/warehouses/hierarchy` using `LocationHierarchyService`.
- Added bulk configuration endpoints:
  - `POST /api/admin/storage-location-config/bulk-update`
  - `POST /api/admin/storage-location-config/bulk-create`
- Utilizes `StorageLocationConfigService.bulk_apply` for batch operations.

## Analytics Controller Updates
- Extended analytics controller with new endpoints:
  - `GET /api/v1/analytics/filter-options`
  - `POST /api/v1/analytics/manual-query`
  - `POST /api/v1/analytics/ai-query`
  - `POST /api/v1/analytics/sales-comparison`
  - `POST /api/v1/analytics/export/large`
- Backed by enhancements in `AnalyticsService` (additional aggregation helpers).
