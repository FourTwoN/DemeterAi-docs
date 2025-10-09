# Master System Overview - DemeterAI ML Pipeline

## Purpose

This diagram provides an **executive-level view** of the complete DemeterAI ML-powered plant counting pipeline, from initial photo upload to final stock batch creation.

## Scope

- **Level**: High-level architectural overview (~50 nodes)
- **Audience**: Technical leads, architects, executives, new developers
- **Detail**: Simplified flow showing major components and their interactions
- **Mermaid Version**: v11.3.0+ (using modern syntax)

## What It Represents

The diagram illustrates the complete journey of a plant cultivation photo through the system:

1. **Client Layer**: User uploads photos via web or mobile client
2. **API Layer**: FastAPI receives request, validates, generates UUIDs, saves temp files, and dispatches async tasks
3. **Celery Workers**: Three types of parallel workers:
   - **I/O workers** (pool=gevent): S3 uploads, extract EXIF, generate thumbnails
   - **GPU workers** (pool=solo): YOLO segmentation and detection, spawn child tasks
   - **CPU workers** (pool=prefork): Aggregate results, create visualizations, generate stock batches
4. **Storage Layer**: PostgreSQL + PostGIS database, AWS S3 buckets, Redis for task coordination
5. **Frontend Polling**: Client polls for task status and displays results

## Key Components

### Critical Path (Highlighted in Red)
The diagram highlights the **critical path** from API entry through task dispatch, showing the fastest route for request processing.

### Architectural Layers (Swimlanes)
- **Client & API**: Request entry point
- **Celery Workers**: Async processing (S3, ML, Callback)
- **Storage**: Database and S3
- **Frontend**: Status polling and results display

### Performance Annotations
Each major step includes:
- ⏱️ **Timing estimates**: Approximate duration
- ⚡ **Parallelism**: Parallel vs. sequential execution
- 🔄 **Retry logic**: Max retries and backoff strategies

### Warning States (Graceful Degradation)
The system handles missing data gracefully:
- **needs_location**: GPS missing or outside cultivation area → Manual location assignment
- **needs_config**: Storage location not configured → Admin configures product/packaging
- **needs_calibration**: Density parameters missing → Manual calibration needed

## Related Detailed Diagrams

For implementation-level details, see:

- **API Entry**: `flows/02_api_entry_detailed.mmd`
- **S3 Upload + Circuit Breaker**: `flows/03_s3_upload_circuit_breaker_detailed.mmd`
- **ML Parent (Segmentation)**: `flows/04_ml_parent_segmentation_detailed.mmd`
- **SAHI Detection**: `flows/05_sahi_detection_child_detailed.mmd`
- **Boxes/Plugs Detection**: `flows/06_boxes_plugs_detection_detailed.mmd`
- **Callback Aggregation**: `flows/07_callback_aggregate_batches_detailed.mmd`
- **Frontend Polling**: `flows/08_frontend_polling_detailed.mmd`

## How It Fits in the System

This overview serves as the **entry point** for understanding the DemeterAI architecture. It shows:

- How photos become inventory records (end-to-end flow)
- Which components run in parallel vs. sequentially
- Where bottlenecks may occur (GPU processing, S3 uploads)
- How the system handles errors and warnings
- The role of each architectural layer

## Technical Highlights

### Modern Mermaid Features Used
- **v11.3.0+ syntax**: All nodes use `@{ shape: X, label: "Y" }` format
- **Semantic shapes**:
  - `stadium` for start/end
  - `subproc` for complex processes
  - `cyl` for database operations
  - `diamond` for decisions
  - `circle` for events
- **Edge IDs**: Critical path edges labeled for styling
- **Swimlanes**: Horizontal layers for architectural clarity

### Color Coding
- **Red**: Errors and critical paths
- **Yellow**: Warnings (graceful degradation)
- **Green**: Success states
- **Blue**: Active processing
- **Orange**: Storage operations

## Usage

Use this diagram to:
- Onboard new team members quickly
- Explain the system to non-technical stakeholders
- Identify integration points for new features
- Understand data flow and dependencies
- Plan scaling strategies (identify bottlenecks)

---

**Version**: 1.0
**Last Updated**: 2025-10-07
**Author**: DemeterAI Engineering Team
