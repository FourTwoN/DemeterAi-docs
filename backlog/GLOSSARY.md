# Glossary - DemeterAI v2.0
## Project Terminology & Acronyms

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**Purpose**: Define all project-specific terms, acronyms, and concepts

---

## A

### Acceptance Criteria (AC)
Specific, testable conditions that must be met for a card to be considered "done". Each card should have 3-5 AC items.

### ADR (Architectural Decision Record)
Document that captures an important architectural decision along with its context and consequences. Stored in `09_decisions/`.

### Alembic
Database migration tool for SQLAlchemy. Manages schema changes over time with upgrade/downgrade scripts.

### AsyncRepository
Base repository pattern class that provides async CRUD operations for database entities. All repositories inherit from this.

---

## B

### Backlog
Collection of all cards not yet started. Located in `03_kanban/00_backlog/`. Cards must meet DoR to move to Ready.

### Band-Based Estimation
ML pipeline technique that divides remaining (undetected) image areas into horizontal bands to estimate plant count. Key innovation: auto-calibrates from real detections.

### Batch (Stock Batch)
Aggregated view of plants grouped by product + packaging + size + location. Table: `stock_batches`.

### Blocker
Dependency or issue preventing a card from progressing. Cards with blockers move to `03_kanban/06_blocked/`.

### Burndown Chart
Graph showing remaining work (story points) over time. Updated daily during sprint.

---

## C

### Celery
Distributed task queue used for async ML processing. **Critical rule**: GPU workers use `pool=solo`.

### Chord Pattern
Celery pattern where multiple child tasks run in parallel, then a callback task runs after all complete. Used in ML pipeline.

### Circuit Breaker
Resilience pattern that prevents cascading failures. Used for S3 uploads (fail fast after 5 consecutive errors).

### Clean Architecture
Architectural pattern with strict dependency rules: Controllers → Services → Repositories → Database. **Never violate Service→Service rule**.

### CPU-First
Design principle: DemeterAI runs on CPU by default, GPU optional for 3-5× speedup. Ensures accessibility without expensive hardware.

### CRUD
Create, Read, Update, Delete - basic database operations. Implemented in Repository layer.

---

## D

### Daily Partitions
Database partitioning strategy for high-volume tables (`detections`, `estimations`). Auto-creates daily partitions with `pg_partman`.

### Definition of Done (DoD)
Checklist a card must meet before moving to Done. Includes: tests ≥80%, code review approved, linting passed, etc.

### Definition of Ready (DoR)
Checklist a card must meet before entering a sprint. Includes: clear AC, dependencies resolved, sized, etc.

### Dependency Injection
Design pattern where dependencies are provided to classes rather than created internally. FastAPI's `Depends()` implements this.

### Detection
Individual plant location identified by YOLO model. Stored in `detections` table (partitioned by date).

### DoD
See Definition of Done.

### DoR
See Definition of Ready.

---

## E

### Epic
High-level feature grouping containing multiple cards. 17 epics in total (e.g., epic-007-ml-pipeline.md).

### Estimation
Area-based plant count for dense regions where individual detection isn't possible. Uses band-based algorithm. Stored in `estimations` table.

### Event Sourcing
Pattern where all changes stored as immutable events. DemeterAI uses hybrid: `stock_movements` (events) + `stock_batches` (aggregated state).

---

## F

### FastAPI
Async-first Python web framework. Version 0.118.2. Auto-generates OpenAPI docs.

### Feathering
Image processing technique that creates soft edges around cropped regions, preventing detection model from treating boundaries as objects.

---

## G

### GPS Localization
Process of extracting GPS coordinates from image EXIF and mapping to `storage_location` via PostGIS ST_Contains query.

### GPU Worker
Celery worker that runs ML inference tasks. **MANDATORY configuration**: `pool=solo, concurrency=1` per GPU.

---

## H

### Handover Briefing
Section in card that provides context for the next developer (why feature exists, key decisions, known limitations).

---

## I

### In-Progress
Kanban column for cards actively being coded. **WIP limit: 5**. Located in `03_kanban/02_in-progress/`.

---

## J

### JWT (JSON Web Token)
Authentication mechanism. Access tokens expire in 15 minutes, refresh tokens in 7 days.

---

## K

### Kanban
Visual workflow management system with columns representing stages (Backlog → Ready → In Progress → Review → Testing → Done).

---

## L

### LAB Color Space
Color representation used in floor/soil suppression (L = lightness, A = green-red, B = blue-yellow).

---

## M

### Manual Initialization
Secondary stock initialization method where user enters count directly (no photo, no ML). Creates `stock_movements` type `manual_init`.

### ML Pipeline
Complete computer vision workflow: Upload → S3 → Segment → Detect (SAHI) → Estimate → Aggregate → Create Batches. **V3 = critical path**.

### Model Singleton
Pattern where ML models loaded once per worker (not per task), preventing 2-3s overhead. Cached in `ModelCache`.

### Monthly Reconciliation
Business workflow: Month start photo → Track movements → Month end photo → Auto-calculate sales = (baseline + movements - new_count).

### Movement Type
Category of stock transaction: `plantar`, `muerte`, `transplante`, `ventas`, `foto`, `manual_init`, `ajuste`.

---

## N

### N+1 Query Problem
Performance anti-pattern where N additional queries executed inside a loop. Solution: Use `selectinload()` or `joinedload()`.

---

## O

### OpenTelemetry (OTLP)
Vendor-neutral observability framework for distributed tracing, metrics, and logs. Exports to Prometheus/Grafana/Tempo stack.

### ORM (Object-Relational Mapping)
SQLAlchemy 2.0.43 - maps Python classes to database tables, enables async queries.

---

## P

### Photo-Based Initialization
Primary stock initialization method using ML pipeline to process photo and generate count. Creates `stock_movements` type `foto`.

### Pydantic
Data validation library (v2.10.0). Used for request/response schemas in FastAPI.

### PostGIS
PostgreSQL extension (v3.3+) for geospatial queries. Enables 4-level location hierarchy with polygon/point operations.

### PostgreSQL 18
Database (⚠️ version 18, NOT 15). 28 tables, event sourcing, daily partitions, SP-GiST indexes.

---

## Q

### Queue
Celery message queue managed by Redis. Three types: `gpu_queue`, `cpu_queue`, `io_queue`.

---

## R

### Ready Column
Kanban column for cards meeting DoR, ready for sprint selection. No WIP limit. Located in `03_kanban/01_ready/`.

### Repository Pattern
Data access layer abstraction. All database queries go through repositories. **Critical**: Services call other services' repositories only via services (never direct repo access).

### Ruff
Linter + formatter (v0.7.0). 10-100× faster than Flake8 + Black. Enforced by pre-commit hooks.

---

## S

### SAHI (Slicing Aided Hyper Inference)
Library for processing large images by tiling. Config: 640×640 slices, 20% overlap, GREEDYNMM merging. +6.8% AP improvement.

### Service Layer
Business logic layer. Coordinates operations, calls other services (NOT repositories directly). Located in `app/services/`.

### Singleton Pattern
Design pattern ensuring only one instance of a class exists. Used for ML models (`ModelCache.get_model()`).

### Sprint
2-week iteration. 6 sprints total = 12 weeks = complete backend. Each sprint has goal, backlog, ceremonies.

### Sprint Planning
2-hour ceremony at sprint start. Team selects cards from Ready, assigns to devs, commits to sprint goal.

### SP-GiST Index
Spatial index type optimized for non-overlapping polygons. Used for `storage_locations.geojson_coordinates`.

### SQLAlchemy
ORM (v2.0.43). Async support, type-safe queries, eager loading. Replaces raw SQL with Python objects.

### Story Point
Relative measure of card complexity (Fibonacci: 1, 2, 3, 5, 8, 13). **NOT time estimate** - accounts for effort + unknowns.

### Stock Movement
Event recording plant transaction. Immutable record in `stock_movements` table. Types: plantar, muerte, transplante, ventas, foto, manual_init, ajuste.

---

## T

### TDD (Test-Driven Development)
Write failing test → Write code to pass test → Refactor. Encouraged (not mandatory) in DemeterAI.

### Tech Stack
Authoritative list of all technology versions. **Single source of truth**: `00_foundation/tech-stack.md`.

---

## U

### UUID (Universally Unique Identifier)
128-bit identifier. Used for `s3_images.image_id` (generated in API, not database SERIAL). Prevents race conditions.

---

## V

### V3 (ML Pipeline Version 3)
Current ML pipeline version. **Critical path** for project - must be completed in Sprint 02. Includes YOLO v11 + SAHI + band-based estimation.

### Velocity
Team's average story points completed per sprint. Target: 80 points/sprint (10 devs × 8 points). Tracked in `01_sprints/velocity-tracking.md`.

---

## W

### Warning State
Non-failure status (e.g., `needs_location`, `needs_config`) indicating manual intervention needed. System creates session but doesn't process until fixed.

### WIP Limit
Maximum cards allowed in Kanban column. **In Progress = 5**, **Code Review = 3**, **Testing = 2**. Prevents bottlenecks.

---

## X

### XL (Story Point Size)
Extra-large card (13 points). **Should be broken down** into multiple smaller cards before sprint planning.

---

## Y

### YOLO v11
Computer vision model from Ultralytics (v8.3.0). Two models: `yolov11m-seg.pt` (segmentation), `yolov11m.pt` (detection). 22% fewer params than v8, 25% faster, CPU-optimized.

---

## Z

### Zone (Storage Area)
Level 2 of location hierarchy: Warehouse → **Storage Area** → Storage Location → Storage Bin. Examples: "North Zone", "South Zone".

---

## Common Acronyms Quick Reference

| Acronym | Full Name | Description |
|---------|-----------|-------------|
| **AC** | Acceptance Criteria | Conditions for card completion |
| **ADR** | Architectural Decision Record | Document capturing key decisions |
| **API** | Application Programming Interface | REST API layer (FastAPI) |
| **CI/CD** | Continuous Integration/Deployment | Automated testing & deployment |
| **CPU** | Central Processing Unit | Primary compute (GPU optional) |
| **CRUD** | Create Read Update Delete | Basic database operations |
| **DB** | Database | PostgreSQL 18 + PostGIS |
| **DoD** | Definition of Done | Completion checklist |
| **DoR** | Definition of Ready | Sprint-readiness checklist |
| **ERD** | Entity-Relationship Diagram | Database schema diagram |
| **GPU** | Graphics Processing Unit | Optional ML accelerator (3-5× speedup) |
| **HSV** | Hue Saturation Value | Color space for vegetation filtering |
| **JWT** | JSON Web Token | Authentication mechanism |
| **ML** | Machine Learning | Computer vision pipeline |
| **ORM** | Object-Relational Mapping | SQLAlchemy database abstraction |
| **OTLP** | OpenTelemetry Protocol | Observability export format |
| **PR** | Pull Request | Code review request (GitHub) |
| **RBAC** | Role-Based Access Control | User permissions system |
| **REST** | Representational State Transfer | API architectural style |
| **SAHI** | Slicing Aided Hyper Inference | Tiling for large images |
| **TDD** | Test-Driven Development | Tests-first coding approach |
| **UUID** | Universally Unique Identifier | 128-bit ID (not SERIAL) |
| **WIP** | Work-In-Progress | Active cards count |
| **YOLO** | You Only Look Once | Object detection algorithm |

---

## Domain-Specific Terms

### Geospatial Hierarchy (4 Levels)

1. **Warehouse** (Level 1): Physical structure (greenhouse, tunnel, shadehouse)
2. **Storage Area** (Level 2): Zone within warehouse (North, South, East, West)
3. **Storage Location** (Level 3): Photo unit - space between columns
4. **Storage Bin** (Level 4): Container (plug, box, segment) dynamically created from segmentation

### Plant States

- **Plug**: Seed germination stage (weeks 1-4)
- **Seedling**: Young plant (weeks 5-12)
- **Juvenile**: Growing phase (weeks 13-26)
- **Mature**: Ready for sale (week 27+)

### Container Types

- **Plug Tray**: Grid of small cells for seed germination (72-200 cells)
- **Box**: Individual container (6-10 cm pot)
- **Segment**: Large growing area (1-3 m² cultivation bed)

---

## Confused About a Term?

1. **Check this glossary first** (Ctrl+F search)
2. **Ask in daily standup** (team knows best)
3. **Update glossary** (if term missing, add it!)
4. **Check engineering plan**: `../../engineering_plan/README.md`

---

**Document Owner**: Technical Writer + Team (crowd-sourced)
**Update Frequency**: Add new terms as project evolves
**Contribution**: Anyone can add/update terms via PR
