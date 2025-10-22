# Frontend Documentation

**Version:** 1.0
**Last Updated:** 2025-10-08

---

## Overview

DemeterAI frontend is designed to provide an intuitive, responsive interface for plant inventory
management across multiple devices (web + mobile).

**Note:** Frontend implementation details are still being finalized. This document outlines the
planned architecture and key views.

---

## Key Views

| View                    | Purpose                                                | Detailed Flow                                                                                 |
|-------------------------|--------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| **Map Views**           | Geographic navigation, warehouse → location drill-down | [../../flows/map_warehouse_views/](../../flows/map_warehouse_views/README.md)                 |
| **Photo Gallery**       | Upload, monitor, error recovery                        | [../../flows/photo_upload_gallery/](../../flows/photo_upload_gallery/README.md)               |
| **Analytics Dashboard** | Reports, comparisons, exports                          | [../../flows/analiticas/](../../flows/analiticas/README.md)                                   |
| **Configuration**       | Storage location config, products, packaging           | [../../flows/location_config/](../../flows/location_config/README.md)                         |
| **Manual Stock Entry**  | Direct count input (no photo)                          | [../../flows/manual_stock_initialization/](../../flows/manual_stock_initialization/README.md) |
| **Price Management**    | Product catalog, pricing                               | [../../flows/price_list_management/](../../flows/price_list_management/README.md)             |

---

## Planned Technology Stack

**Framework:** React or Vue.js (TBD)
**State Management:** Redux or Pinia (TBD)
**Map Library:** Leaflet or Mapbox (for PostGIS polygon rendering)
**UI Components:** Material-UI or Tailwind CSS (TBD)
**HTTP Client:** Axios (async API calls)

---

## Map View Architecture

**Purpose:** Navigate warehouse hierarchy visually

**Flow:**

1. **Warehouse Map:** Display all warehouses on map (PostGIS polygons)
2. **Click Warehouse:** Drill-down to storage areas
3. **Click Storage Area:** Drill-down to storage locations
4. **Click Storage Location:** Show detail + photo gallery + stock

**Features:**

- Color-coded by stock level (green = good, yellow = low, red = empty)
- Filter by product/packaging
- Search by QR code

**See:** [../../flows/map_warehouse_views/](../../flows/map_warehouse_views/README.md)

---

## Photo Upload Gallery

**Purpose:** Batch photo upload + real-time processing status

**Flow:**

1. **Upload:** Select multiple photos (up to 50)
2. **Monitor:** Real-time progress bars per photo
3. **Results:** Display processed images with counts
4. **Errors:** Retry failed uploads

**Features:**

- Drag-and-drop upload
- Thumbnail previews
- Polling for async status (GET /api/stock/tasks/status)

**See:** [../../flows/photo_upload_gallery/](../../flows/photo_upload_gallery/README.md)

---

## Manual Stock Entry Form

**Purpose:** Enter stock count without photo

**Fields:**

- Storage Location (dropdown or QR scan)
- Product (dropdown, filtered by config if exists)
- Packaging (dropdown, filtered by config if exists)
- Product Size (optional)
- Quantity (required, > 0)
- Planting Date (optional)
- Notes (optional)

**Validation:**

- **CRITICAL:** If config exists, product/packaging must match
- **Error display:** User-friendly message + suggested actions
- **Success:** Redirect to location detail page

**See:
** [../../flows/manual_stock_initialization/](../../flows/manual_stock_initialization/README.md)

---

## Analytics Dashboard

**Purpose:** Data visualization + export

**Features:**

- Multiple chart types (bar, line, pie)
- Grouping options (warehouse, product, packaging)
- Date range filters
- Sales vs. stock comparisons
- Export to Excel/CSV

**See:** [../../flows/analiticas/](../../flows/analiticas/README.md)

---

## Configuration Views

**Purpose:** Manage storage_location_config

**Features:**

- List view: All configured locations
- Edit form: Update product/packaging expectations
- Bulk operations: Configure multiple locations at once

**See:** [../../flows/location_config/](../../flows/location_config/README.md)

---

## Responsive Design

**Mobile-first approach:**

- Photo upload: Native camera integration
- QR scanning: Built-in scanner
- Map navigation: Touch-optimized
- Forms: Large touch targets

**Breakpoints:**

- Mobile: <768px
- Tablet: 768-1024px
- Desktop: >1024px

---

## Next Steps

- **Detailed Flow Diagrams:** See [../../flows/](../../flows/)
- **API Integration:** See [../api/README.md](../api/README.md)
- **Backend Services:** See [../backend/README.md](../backend/README.md)

---

**Document Owner:** DemeterAI Engineering Team
**Status:** Planning Phase
**Last Reviewed:** 2025-10-08
