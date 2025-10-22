# Workflows - DemeterAI v2.0

**Document Version:** 1.0
**Last Updated:** 2025-10-08

---

## Overview

This directory contains **high-level summaries** of all major business workflows in DemeterAI. Each
summary links to detailed Mermaid diagrams in the `../flows/` directory.

### Purpose

- **Quick reference** for developers to understand business logic
- **Entry point** before diving into detailed flow diagrams
- **Traceability** from business requirements → implementation

---

## Workflow Index

| Workflow                   | Summary                                                | Detailed Diagrams                                                                                   |
|----------------------------|--------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| **Photo Initialization**   | ML-powered stock counting from photos                  | [procesamiento_ml_upload_s3_principal/](../../flows/procesamiento_ml_upload_s3_principal/README.md) |
| **Manual Initialization**  | Direct stock count entry (no photo/ML)                 | [manual_stock_initialization/](../../flows/manual_stock_initialization/README.md)                   |
| **Stock Movements**        | Plantado, muerte, transplante, ventas tracking         | [stock_movements/](../../flows/stock_movements/)                                                    |
| **Monthly Reconciliation** | Month-end photo → automatic sales calculation          | *(See photo_initialization.md)*                                                                     |
| **Photo Gallery**          | Upload tracking, job monitoring, error recovery        | [photo_upload_gallery/](../../flows/photo_upload_gallery/README.md)                                 |
| **Map Views**              | Geographic navigation, warehouse → location drill-down | [map_warehouse_views/](../../flows/map_warehouse_views/README.md)                                   |
| **Analytics**              | Reports, comparisons, data export                      | [analiticas/](../../flows/analiticas/README.md)                                                     |
| **Location Configuration** | Configure expected product + packaging per location    | [location_config/](../../flows/location_config/README.md)                                           |
| **Price Management**       | Product catalog, packaging catalog, price lists        | [price_list_management/](../../flows/price_list_management/README.md)                               |

---

## Workflow Summaries

### 1. Photo Initialization (Primary Method)

**File:** [photo_initialization.md](./photo_initialization.md)

**What it does:**

- User uploads photo via web/mobile
- ML pipeline (YOLO v11 + SAHI) processes image
- Detects containers (plugs, boxes, segments)
- Counts individual plants (detection)
- Estimates plants in dense areas (estimation)
- Creates `stock_movements` (type: `"foto"`) + `stock_batches`

**Output:**

- Detections (individual plant locations)
- Estimations (area-based counts)
- Visualized image (circles + masks)
- Stock batches (grouped by product + size + packaging)

**Detailed Diagrams:
** [../flows/procesamiento_ml_upload_s3_principal/](../../flows/procesamiento_ml_upload_s3_principal/README.md)

---

### 2. Manual Initialization (Secondary Method) **NEW**

**File:** [manual_initialization.md](./manual_initialization.md)

**What it does:**

- User enters complete count via UI
- System validates against `storage_location_config`
- **CRITICAL:** Must match expected product + packaging
- Creates `stock_movements` (type: `"manual_init"`) + `stock_batches`
- NO photo, detections, estimations, or ML processing

**Output:**

- Stock movement record (manual source)
- Stock batch (product + size + packaging + quantity)

**Use Case:**

- User already has pre-counted stock (legacy data)
- Photo system temporarily unavailable
- Fallback when GPS/config/calibration missing

**Detailed Diagrams:
** [../flows/manual_stock_initialization/](../../flows/manual_stock_initialization/README.md)

---

### 3. Stock Movements (Throughout Month)

**What it does:**

- Track plant movements during the month
- Types: `plantado`, `muerte`, `transplante`, `ventas`, `ajuste`
- Each movement creates `stock_movements` record
- Updates `stock_batches.quantity_current`

**Movement Types:**

| Type          | Description                     | Ingress/Egress | Example                               |
|---------------|---------------------------------|----------------|---------------------------------------|
| `plantar`     | New plantings                   | Ingress (+)    | 500 new plugs planted                 |
| `sembrar`     | Sowing seeds                    | Ingress (+)    | 1000 seeds sown                       |
| `transplante` | Move to different location/size | Transfer (±)   | 200 plants moved from plug → seedling |
| `muerte`      | Plant deaths                    | Egress (-)     | 50 plants died                        |
| `ventas`      | Sales (calculated or manual)    | Egress (-)     | 300 plants sold                       |
| `ajuste`      | Manual adjustments              | Either         | Correct count error                   |
| `foto`        | Photo initialization            | Ingress (+)    | Initial count from photo              |
| `manual_init` | Manual initialization           | Ingress (+)    | Initial count manually entered        |

---

### 4. Monthly Reconciliation

**What it does:**

- **Month Start:** Photo or manual initialization (baseline count)
- **During Month:** Track movements (plantado, muerte, transplante)
- **Month End:** New photo → automatic sales calculation
  ```
  sales = (baseline + plantado - muerte - transplante_out) - new_photo_count
  ```
- **Validation:** Compare with client CSV data

**Why it matters:**

- Automates sales tracking (no manual counting)
- Detects anomalies (missing plants = theft/errors)
- Builds historical data for forecasting

**Example:**

```
Jan 1:  Baseline = 10,000 plants (photo)
Jan:    +500 plantado, -200 muerte, -300 transplante
Jan 31: New photo = 9,500 plants
        Sales = (10,000 + 500 - 200 - 300) - 9,500 = 500 plants ✓
```

---

### 5. Photo Upload Gallery

**File:** [Photo Gallery Overview](../../flows/photo_upload_gallery/README.md)

**What it does:**

- Upload multiple photos simultaneously
- Monitor processing jobs in real-time
- Display processed images in gallery
- Handle errors + reprocessing

**Key Features:**

- Batch upload (up to 50 photos)
- Progress tracking per photo
- Error recovery (retry failed uploads)
- Thumbnail generation (400×400 AVIF)

---

### 6. Map Warehouse Views

**File:** [Map Views Overview](../../flows/map_warehouse_views/README.md)

**What it does:**

- Display all warehouses on map
- Drill-down: Warehouse → Storage Area → Storage Location
- Preview counts per location
- Historical timeline view

**Key Features:**

- Interactive map (PostGIS polygons)
- Color-coded by stock level
- Click location → see detail
- Filter by product/packaging

---

### 7. Analytics

**File:** [Analytics Overview](../../flows/analiticas/README.md)

**What it does:**

- Manual filter-based reports
- Sales vs. stock comparisons
- Data export (Excel/CSV)
- AI-powered analytics (future: marked PENDING)

**Key Features:**

- Multiple grouping options (warehouse, product, packaging)
- Date range filters
- Comparison mode (this month vs. last month)
- Export to external systems

---

### 8. Location Configuration

**File:** [Location Config Overview](../../flows/location_config/README.md)

**What it does:**

- Configure expected product + packaging per `storage_location`
- Used for ML classification validation
- **CRITICAL for manual initialization:** Validates product match

**Configuration Fields:**

- `product_id` (expected species)
- `packaging_catalog_id` (expected pot type)
- `expected_product_state_id` (plug, seedling, sellable)
- `area_cm2` (physical area)

**Why it matters:**

- ML pipeline uses config to assign classification
- Manual initialization validates against config
- Analytics filters by configured products

---

### 9. Price Management

**File:** [Price Management Overview](../../flows/price_list_management/README.md)

**What it does:**

- Manage product catalog (species, families, categories)
- Manage packaging catalog (pot types, materials, colors)
- Create price lists (wholesale + retail pricing)
- Bulk edit operations

**Key Features:**

- Hierarchical product structure (category → family → product)
- SKU generation
- Price list versioning
- Discount factor management

---

## Workflow Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                     INITIALIZATION                               │
│  ┌───────────────────────┬───────────────────────────┐          │
│  │  Photo Init           │  Manual Init              │          │
│  │  (ML pipeline)        │  (Direct entry)           │          │
│  └───────────┬───────────┴───────────┬───────────────┘          │
└──────────────┼─────────────────────────┼────────────────────────┘
               └─────────────┬───────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                     STOCK MOVEMENTS                              │
│  ┌───────────────────────────────────────────────────┐          │
│  │  Plantado, Muerte, Transplante, Ajuste            │          │
│  └───────────────────────┬───────────────────────────┘          │
└────────────────────────────┼────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                MONTHLY RECONCILIATION                            │
│  ┌───────────────────────────────────────────────────┐          │
│  │  Month-end photo → Calculate sales                │          │
│  └───────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                      ANALYTICS                                   │
│  ┌───────────────────────────────────────────────────┐          │
│  │  Reports, Exports, Comparisons                    │          │
│  └───────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## How to Use This Directory

### For Developers

1. **Start here:** Read workflow summaries to understand business logic
2. **Dive deeper:** Follow links to detailed Mermaid diagrams
3. **Implement:** Use backend documentation for technical details

### For Product Managers

1. **Business context:** Read summaries to understand what the system does
2. **Validation:** Verify workflows match business requirements
3. **Planning:** Identify gaps or improvements

### For New Team Members

1. **Month 1:** Read all workflow summaries (2-3 hours)
2. **Month 2:** Study detailed diagrams for assigned features
3. **Month 3:** Implement features using workflow + backend docs

---

## Next Steps

- **Detailed Flows:** See [../flows/](../../flows/) for Mermaid diagrams
- **Backend Implementation:** See [../backend/README.md](../backend/README.md)
- **API Endpoints:** See [../api/README.md](../api/README.md)

---

**Document Owner:** DemeterAI Engineering Team
**Last Reviewed:** 2025-10-08
