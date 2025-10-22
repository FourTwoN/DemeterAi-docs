# DemeterAI v2.0 - Engineering Documentation

**Version:** 2.0
**Last Updated:** 2025-10-08
**Status:** Production-Ready Design Phase

---

## Quick Links

| Section                                       | Description                                    |
|-----------------------------------------------|------------------------------------------------|
| [Project Overview](./01_project_overview.md)  | Business context, objectives, key requirements |
| [Technology Stack](./02_technology_stack.md)  | Languages, frameworks, versions, rationale     |
| [Architecture](./03_architecture_overview.md) | System layers, patterns, clean architecture    |
| [Database](./database/README.md)              | Schema, decisions, indexing strategy           |
| [Workflows](./workflows/README.md)            | Photo/manual initialization, stock movements   |
| [Backend](./backend/README.md)                | Repository, service, controller, ML pipeline   |
| [API](./api/README.md)                        | REST endpoints specification                   |
| [Frontend](./frontend/README.md)              | Views, components, user flows                  |
| [Deployment](./deployment/README.md)          | Docker, Celery, monitoring                     |
| [Development](./development/README.md)        | Phases, conventions, testing                   |

---

## What is DemeterAI?

DemeterAI is an **ML-powered automated plant counting and inventory management system** designed to
handle **600,000+ cacti and succulents** across multiple cultivation zones.

### Core Value Proposition

Transform photos of cultivation areas into accurate, geocoded inventory counts with full
traceability, supporting monthly reconciliation workflows that detect sales, deaths, and transplants
automatically.

**Key Results:**

- 90% less waste
- 80% reduced administrative time
- 100% accuracy in production and shipping

---

## System at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                                │
│                  Web Frontend + Mobile App                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      API LAYER                                   │
│            FastAPI 0.118 (Async-first REST API)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   CELERY WORKERS                                 │
│  GPU Workers (pool=solo) │ CPU Workers │ I/O Workers (gevent)   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   STORAGE LAYER                                  │
│  PostgreSQL 15 + PostGIS │ AWS S3 │ Redis 7                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Two Initialization Methods

DemeterAI supports **TWO ways** to initialize stock for a storage location:

### 1. Photo-Based Initialization (Primary)

- User uploads photo
- ML pipeline (YOLO v11 + SAHI) detects and estimates plants
- Creates: `photo_processing_sessions` → `detections` → `estimations` → `stock_movements` (type:
  `"foto"`)
- **95%+ accuracy**, CPU-first approach (5-10 min per photo)

**Workflow:**
See [Photo Initialization](./workflows/photo_initialization.md) → [Detailed Flow](../flows/procesamiento_ml_upload_s3_principal/README.md)

### 2. Manual Initialization (Secondary)

- User enters complete count via UI
- Configuration validation (CRITICAL: must match expected product/packaging)
- Creates: `stock_movements` (type: `"manual_init"`) → `stock_batches`
- **No photo, no ML** - trusts user input
- **Use case:** User already has pre-counted stock

**Workflow:**
See [Manual Initialization](./workflows/manual_initialization.md) → [Detailed Flow](../flows/manual_stock_initialization/README.md)

---

## Monthly Reconciliation Pattern

```
Month Start: Photo OR Manual init (baseline)
     ↓
During Month: Movements (plantado, muerte, transplante)
     ↓
Month End: Next photo → Automatically calculates SALES
     Formula: sales = previous + movements - current_count
     ↓
Validation: CSV from client with actual sales data
```

---

## Technology Highlights

| Layer             | Technology           | Version  | Why                            |
|-------------------|----------------------|----------|--------------------------------|
| **Language**      | Python               | 3.12     | Latest stable, async support   |
| **Web Framework** | FastAPI              | 0.118.2  | Async-first, auto OpenAPI docs |
| **ORM**           | SQLAlchemy           | 2.0.43   | Async support, type-safe       |
| **Database**      | PostgreSQL + PostGIS | 15 + 3.3 | Geospatial queries, ACID       |
| **Task Queue**    | Celery + Redis       | 5.3 + 7  | Chord patterns, DLQ            |
| **ML Framework**  | Ultralytics YOLO     | v11      | 22% fewer params, 25% faster   |
| **CV Library**    | SAHI                 | Latest   | +6.8% AP for high-res images   |

**CRITICAL:** DemeterAI is **CPU-first**. GPU is optional for 3-5× speedup, but the entire system is
designed to run on CPU (5-10 min/photo).

---

## Documentation Structure

This engineering documentation follows a **hierarchical, reference-based structure**:

### Levels of Detail

1. **Engineering Plan** (this folder): High-level summaries + cross-references
2. **Flows** (`../flows/`): Detailed Mermaid diagrams with step-by-step flows
3. **Database** (`../database/`): Complete ERD + schema documentation
4. **Context** (`../context/`): Technical decisions, past conversations

### How to Navigate

- **Start here:** [01_project_overview.md](./01_project_overview.md)
- **Understand the system:** [03_architecture_overview.md](./03_architecture_overview.md)
- **Implement features:
  ** [workflows/README.md](./workflows/README.md) → [backend/README.md](./backend/README.md) → [api/README.md](./api/README.md)
- **Deploy:** [deployment/README.md](./deployment/README.md)

---

## Quick Reference: File Sizes

- **Small files (50-150 lines):** Quick lookups, focused topics
- **Medium files (150-300 lines):** Complete subsystems
- **Large files (300-500 lines):** Comprehensive guides

**Old vs. New:**

- ❌ **Old:** 1 file, 3155 lines (overwhelming)
- ✅ **New:** 21 files, 50-300 lines each (navigable)

---

## Migration Note

This documentation structure **replaces** the previous monolithic `engineering_doc.md` (now archived
as `_ARCHIVED_engineering_doc_v1.md`).

**Key improvements:**

- ✅ Modular, focused documents
- ✅ Cross-references to detailed flows
- ✅ Updated to latest technologies (2025)
- ✅ Includes manual initialization workflow
- ✅ CPU-first approach prominently highlighted

---

## For New Team Members

**Step 1:** Read [01_project_overview.md](./01_project_overview.md) to understand WHAT and WHY
**Step 2:** Review [02_technology_stack.md](./02_technology_stack.md) to understand HOW
**Step 3:** Study [03_architecture_overview.md](./03_architecture_overview.md) to understand
STRUCTURE
**Step 4:** Pick a workflow in [workflows/README.md](./workflows/README.md) and implement it

**Time to onboard:** ~2-4 hours to understand the full system

---

## For Claude Code

When working on DemeterAI:

1. **Database = Source of Truth:** Always consult [database/README.md](./database/README.md) first
2. **Follow workflows:** Use [workflows/README.md](./workflows/README.md) to understand business
   logic
3. **Check existing flows:** Before creating new diagrams, see [../flows/](../flows/)
4. **Validate Mermaid:** Always run
   `mmdc -i diagram.mmd -o /tmp/test.png --puppeteerConfigFile <(echo '{"args":["--no-sandbox"]}')`
5. **Commit frequently:** Use format `docs: <description>`

---

**Last Updated:** 2025-10-08
**Maintained By:** DemeterAI Engineering Team
**Version Control:** Git repository `/home/lucasg/proyectos/DemeterDocs`
