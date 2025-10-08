# Project Overview - DemeterAI v2.0

**Document Version:** 1.0
**Last Updated:** 2025-10-08

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Business Context](#business-context)
3. [The Problem](#the-problem)
4. [The Solution](#the-solution)
5. [Key Stakeholders](#key-stakeholders)
6. [Success Metrics](#success-metrics)
7. [Project Scope](#project-scope)

---

## Executive Summary

**DemeterAI** is a production-grade **automated plant counting and inventory management system** designed to replace manual, error-prone stock-taking processes for a large-scale cactus and succulent cultivation operation managing **600,000+ plants** across multiple greenhouses and cultivation zones.

### The Mission

Transform plant inventory management from a time-consuming, inaccurate manual process to a **90% automated, ML-powered system** that delivers:

- **90% less waste** from inventory errors
- **80% reduction** in administrative time
- **100% accuracy** in production and shipping
- **Real-time visibility** into stock levels and movements

---

## Business Context

### Cultivation Scale

- **Total Plants:** 600,000+ cacti and succulents
- **Warehouses:** Multiple greenhouses, shadehouses, tunnels, open fields
- **Product Categories:** 100+ species and varieties
- **Packaging Types:** 50+ pot types (plugs, trays, boxes, segments)
- **Monthly Movements:** Thousands of plantings, transplants, deaths, sales

### Current Process (Manual)

**How it works today:**

1. Workers manually count plants in each cultivation zone
2. Counts recorded on paper or basic spreadsheets
3. Infrequent updates (monthly or less)
4. Sales calculated manually from client orders
5. Inventory discrepancies discovered too late

**Pain Points:**

- ❌ **Time-intensive:** 4-6 hours to count a single greenhouse
- ❌ **Error-prone:** Human counting errors 15-20% in dense areas
- ❌ **No traceability:** Cannot track individual plant movements
- ❌ **Delayed insights:** Weeks to detect problems
- ❌ **Waste:** Plants die or become unsellable due to poor tracking

---

## The Problem

### Core Challenges

1. **Scale:** 600,000+ plants make manual counting impractical
2. **Accuracy:** Dense cultivation makes individual plant counting extremely difficult
3. **Traceability:** No way to track plant history (planting date, growth stage, movements)
4. **Monthly Reconciliation:** Cannot accurately calculate sales without reliable counts
5. **Multiple Stages:** Plants move through 4 stages (plug → seedling → box → segment)
6. **Geographic Complexity:** 4-level hierarchy (warehouse → area → location → bin)

### What Happens Without a Solution

- Plants die unnoticed in remote greenhouses
- Over/under-production due to inaccurate forecasts
- Client orders delayed due to inventory errors
- Manual labor costs escalate
- No data-driven insights for optimization

---

## The Solution

### DemeterAI System

An **ML-powered inventory management system** that combines:

1. **Computer Vision (YOLO v11 + SAHI)**
   - Automated plant detection and counting from photos
   - 95%+ accuracy in real cultivation conditions
   - CPU-first design (GPU optional for 3-5× speedup)

2. **Geospatial Database (PostgreSQL + PostGIS)**
   - 4-level location hierarchy
   - Point-in-polygon geocoding from GPS metadata
   - Full audit trail of all movements

3. **Two Initialization Methods**
   - **Photo-based:** ML pipeline (primary method)
   - **Manual entry:** Direct count input (fallback/legacy)

4. **Monthly Reconciliation Workflow**
   - Baseline photo/count at month start
   - Track movements (plantings, deaths, transplants)
   - End-of-month photo → **automatic sales calculation**
   - External validation via client CSV data

### How It Works (High-Level)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. CAPTURE: User uploads photo via mobile/web                  │
│     → GPS metadata extracted                                     │
│     → Image uploaded to S3                                       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. PROCESS: ML pipeline (YOLO v11)                             │
│     → Segmentation: Find containers (plugs, boxes, segments)    │
│     → Detection: Count individual plants (SAHI for high-res)    │
│     → Estimation: Calculate plants in dense areas               │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. CLASSIFY: Assign product + packaging                        │
│     → Retrieve storage_location_config from database            │
│     → Validate: Expected product matches detected category      │
│     → Warning if mismatch (graceful degradation)                │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. STORE: Create inventory records                             │
│     → stock_movements (type: "foto" or "manual_init")           │
│     → stock_batches (grouped by product + size + packaging)     │
│     → detections + estimations (ML results)                     │
│     → photo_processing_sessions (metadata + results)            │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. VISUALIZE: Dashboard and reports                            │
│     → Map view: See all greenhouses with counts                 │
│     → Timeline: Track changes over time                         │
│     → Analytics: Compare sales vs. stock vs. production         │
│     → Export: Excel/CSV for external systems                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Stakeholders

### Primary Users

| Role | Needs | How DemeterAI Helps |
|------|-------|---------------------|
| **Field Workers** | Fast, easy plant counting | Upload photo, get instant count |
| **Supervisors** | Monitor multiple greenhouses | Real-time dashboard, map views |
| **Administrators** | Configure products, analyze trends | Powerful analytics, export reports |
| **Company Owners** | Reduce waste, increase profit | Data-driven insights, automated reconciliation |

### System Roles (Technical)

- **Admin:** Full access, configure system, manage users
- **Supervisor:** View all data, approve counts, run reports
- **Worker:** Upload photos, enter manual counts
- **Viewer:** Read-only access to dashboards

---

## Success Metrics

### Quantitative Goals

| Metric | Current (Manual) | Target (DemeterAI) | Improvement |
|--------|------------------|-------------------|-------------|
| **Counting Time** | 4-6 hours/greenhouse | 10-15 min/greenhouse | **90% reduction** |
| **Accuracy** | 80-85% (manual) | 95%+ (ML) | **15-20% improvement** |
| **Administrative Time** | 20 hours/week | 4 hours/week | **80% reduction** |
| **Waste from Errors** | 10-15% of stock | <2% | **90% waste reduction** |
| **Inventory Visibility** | Monthly | Real-time | **100% visibility** |

### Qualitative Goals

- ✅ **Traceability:** Full audit trail for every plant movement
- ✅ **Confidence:** Automated sales calculation removes guesswork
- ✅ **Scalability:** System handles 600k plants, can scale to millions
- ✅ **Flexibility:** Supports both photo and manual workflows
- ✅ **Reliability:** CPU-first approach works without GPU hardware

---

## Project Scope

### Phase: Engineering Design & Documentation (Current)

**Goal:** Create comprehensive technical documentation that enables development team to implement DemeterAI v2.0 efficiently.

**Deliverables:**

1. ✅ Complete database schema (PostgreSQL + PostGIS)
2. ✅ Detailed workflow diagrams (6 major workflows documented)
3. ✅ Engineering architecture documentation (this folder)
4. ✅ ML pipeline specification (YOLO v11 + SAHI)
5. ✅ API endpoint design (REST with FastAPI)

### Future Phases

**Phase 0:** Repository setup, virtual env, dependencies
**Phase 1-5:** Backend (repositories, services, ML pipeline, schemas)
**Phase 6-10:** API (controllers, Celery, analytics, auth)
**Phase 11-15:** Infrastructure (exceptions, logging, Docker, optimization)

See [Development Phases](./development/phases.md) for detailed roadmap.

### Out of Scope (Current Phase)

- ❌ Frontend implementation (UI/UX design pending)
- ❌ Production deployment (infrastructure decisions pending)
- ❌ Client-specific integrations (CSV import formats vary)
- ❌ Advanced AI features (generative analytics marked as PENDING)

---

## Monthly Reconciliation Pattern (Critical Business Logic)

### The Workflow

```
┌────────────────────────────────────────────────────────────────┐
│  MONTH START (January 1)                                       │
│  ─────────────────────────                                      │
│  Photo OR Manual Init → Baseline Count: 10,000 plants          │
│  Stored as: stock_movements (type: "foto" or "manual_init")    │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│  DURING MONTH (Jan 1-31)                                       │
│  ────────────────────────                                       │
│  Manual Movements Tracked:                                     │
│    + Plantado (new plantings):     +500                        │
│    - Muerte (plant deaths):        -200                        │
│    - Transplante (moved to other):  -300                       │
│                                                                 │
│  Expected Count = 10,000 + 500 - 200 - 300 = 10,000           │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│  MONTH END (January 31)                                        │
│  ─────────────────────────                                      │
│  New Photo Taken → Detected Count: 9,500 plants                │
│                                                                 │
│  SALES CALCULATION (Automatic):                                │
│  sales = (10,000 + 500 - 200 - 300) - 9,500 = 500 plants      │
│                                                                 │
│  Created as: stock_movements (type: "ventas", quantity: -500)  │
└────────────────────────┬───────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────────┐
│  EXTERNAL VALIDATION                                           │
│  ───────────────────────                                        │
│  CSV from Client: 500 units purchased (matches!)               │
│  Admin Reviews: ✅ Reconciled                                  │
│                                                                 │
│  If mismatch: Investigate (theft, errors, untracked deaths)    │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Matters

- **Automates sales tracking:** No manual counting of sold plants
- **Detects anomalies:** Missing plants = investigation needed
- **Builds trust:** External validation confirms accuracy
- **Enables forecasting:** Historical data drives production planning

---

## Next Steps

1. **Read:** [Technology Stack](./02_technology_stack.md) to understand HOW we build this
2. **Read:** [Architecture Overview](./03_architecture_overview.md) to understand STRUCTURE
3. **Dive Deeper:** [Workflows](./workflows/README.md) to understand BUSINESS LOGIC
4. **Implement:** [Development Guide](./development/README.md) to start building

---

**Document Owner:** DemeterAI Engineering Team
**Review Cycle:** Quarterly or when major requirements change
**Feedback:** Update `context/past_chats_summary.md` with new decisions
