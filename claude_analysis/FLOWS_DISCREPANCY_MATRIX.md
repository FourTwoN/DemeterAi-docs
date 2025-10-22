# MATRIZ DE DISCREPANCIAS: FLUJOS vs CÓDIGO

**Auditoría**: 2025-10-21 | **Versión**: 1.0

## LEYENDA

- ✅ = Implementado y sincronizado
- ⚠️ = Parcialmente implementado
- ❌ = No implementado
- ⛔ = Crítico/Bloqueante

---

## 1. ML PROCESSING PIPELINE

| Componente                        | Descripción                         | Diagrama  | Código | Estado | Prioridad |
|-----------------------------------|-------------------------------------|-----------|--------|--------|-----------|
| **LAYER 1: API Entry**            |                                     |           |        |        |           |
| API Endpoint                      | POST /api/stock/photo               | ✅ v2      | ✅      | ✅      | 🟢        |
| Validation                        | Content-Type, Size, Format          | ✅         | ✅      | ✅      | 🟢        |
| UUID Generation                   | Generate UUID v4                    | ✅         | ✅      | ✅      | 🟢        |
| Temp Storage                      | Save /tmp/uploads/                  | ✅         | ✅      | ✅      | 🟢        |
| DB Insert                         | INSERT s3_images                    | ✅         | ✅      | ✅      | 🟢        |
| Chunking                          | 20 for S3, 1 for ML                 | ✅         | ⚠️     | ⚠️     | 🟡        |
| Task Dispatch                     | Launch Celery parallel              | ✅         | ✅      | ✅      | 🟢        |
| Response                          | 202 Accepted                        | ✅         | ✅      | ✅      | 🟢        |
| **LAYER 2a: S3 Upload**           |                                     |           |        |        |           |
| Circuit Breaker                   | Check state, Open on threshold      | ✅         | ⚠️     | ⚠️     | 🟡        |
| EXIF Extraction                   | GPS, timestamp, camera              | ✅         | ✅      | ✅      | 🟢        |
| S3 Upload                         | Upload to /original/YYYY/MM/DD      | ✅         | ✅      | ✅      | 🟢        |
| Thumbnail Gen                     | 400x400 LANCZOS                     | ✅         | ✅      | ✅      | 🟢        |
| AVIF Compression                  | quality=85, 50% reduction           | ✅         | ❌      | ❌      | 🔴        |
| Thumbnail Upload                  | /thumbnails/                        | ✅         | ✅      | ⚠️     | 🟡        |
| DB Update                         | status='ready'                      | ✅         | ✅      | ✅      | 🟢        |
| **LAYER 2b: ML Parent**           |                                     |           |        |        |           |
| Model Loading                     | YOLO v11, Singleton pattern         | ✅         | ⚠️     | ⚠️     | 🟡        |
| Geolocation                       | PostGIS ST_Contains                 | ✅         | ✅      | ✅      | 🟢        |
| GPS Warning                       | needs_location flag                 | ✅         | ✅      | ✅      | 🟢        |
| Config Query                      | Get config for location             | ✅         | ✅      | ✅      | 🟢        |
| Config Warning                    | needs_config flag                   | ✅         | ✅      | ✅      | 🟢        |
| Density Query                     | Get density parameters              | ✅         | ✅      | ✅      | 🟢        |
| Density Warning                   | needs_calibration flag              | ✅         | ✅      | ✅      | 🟢        |
| Session Create                    | INSERT photo_processing_sessions    | ✅         | ✅      | ✅      | 🟢        |
| YOLO Segment                      | conf=0.30, iou=0.50, imgsz=1024     | ✅         | ✅      | ✅      | 🟢        |
| Mask Processing                   | Morphological smoothing, fill holes | ✅         | ✅      | ✅      | 🟢        |
| Mask Classify                     | segment/cajon/almacigo/plug         | ✅         | ✅      | ✅      | 🟢        |
| Chord Pattern                     | group(*tasks) + callback            | ✅         | ✅      | ✅      | 🟢        |
| **LAYER 2c: Child Tasks (SAHI)**  |                                     |           |        |        |           |
| SAHI Detection                    | Slicing + inference 640x640         | ✅         | ❌      | ❌      | 🔴        |
| Stock Movement Create             | INSERT stock_movements              | ✅         | ❌      | ❌      | 🔴        |
| Detection Bulk Insert             | BULK INSERT detections              | ✅         | ❌      | ❌      | 🔴        |
| Estimation                        | Area remaining + band analysis      | ✅         | ❌      | ❌      | 🔴        |
| Density Calibration               | Update density_parameters           | ✅         | ❌      | ❌      | 🔴        |
| Estimation Insert                 | INSERT estimations                  | ✅         | ❌      | ❌      | 🔴        |
| Movement Update                   | Link to batch                       | ✅         | ❌      | ❌      | 🔴        |
| **LAYER 2d: Child Tasks (Boxes)** |                                     |           |        |        |           |
| Direct Detection                  | YOLO without SAHI                   | ✅         | ❌      | ❌      | 🔴        |
| Detection Insert                  | Same as SAHI                        | ✅         | ❌      | ❌      | 🔴        |
| Estimation                        | Same as SAHI                        | ✅         | ❌      | ❌      | 🔴        |
| **LAYER 2e: Callback**            |                                     |           |        |        |           |
| Aggregate Results                 | Sum totals + avg confidence         | ✅         | ❌      | ❌      | 🔴        |
| Visualization                     | Draw circles + masks                | ✅         | ❌      | ❌      | 🔴        |
| Viz Upload                        | S3 processed/YYYY/MM/DD             | ✅         | ❌      | ❌      | 🔴        |
| Batch Creation                    | Group by classification             | ✅         | ❌      | ❌      | 🔴        |
| Batch Code Gen                    | LOC-PROD-YYYYMMDD-seq               | ✅         | ⚠️     | ⚠️     | 🟡        |
| Verification                      | FK check + consistency              | ✅         | ❌      | ❌      | 🔴        |
| Rollback                          | DELETE batches on error             | ✅         | ❌      | ❌      | 🔴        |
| Session Update                    | status='completed'                  | ✅         | ❌      | ❌      | 🔴        |
| **LAYER 3: Frontend**             |                                     |           |        |        |           |
| Poll Status                       | GET /api/stock/tasks/status         | ✅         | ⚠️     | ⚠️     | 🟡        |
| Display Results                   | Gallery + batches                   | ✅         | ❌      | ❌      | 🔴        |
| **TOTAL ML PIPELINE**             |                                     | **9 sub** | 40%    | ⛔      | 🔴        |

---

## 2. PHOTO GALLERY & UPLOAD

| Componente              | Descripción                 | Diagrama  | Código | Estado | Prioridad |
|-------------------------|-----------------------------|-----------|--------|--------|-----------|
| **Upload Phase**        |                             |           |        |        |           |
| Upload Endpoint         | POST /api/photos/upload     | ✅         | ✅      | ✅      | 🟢        |
| Multipart Handling      | Handle multiple files       | ✅         | ✅      | ✅      | 🟢        |
| Job Creation            | Create Celery jobs          | ✅         | ✅      | ✅      | 🟢        |
| Return 202              | Accepted response           | ✅         | ✅      | ✅      | 🟢        |
| **Job Monitoring**      |                             |           |        |        |           |
| Polling Endpoint        | GET /api/jobs/status        | ✅         | ⚠️     | ⚠️     | 🟡        |
| Exponential Backoff     | Increase poll interval      | ✅         | ❌      | ❌      | 🔴        |
| Status Display          | Show progress bar           | ✅         | ❌      | ❌      | 🔴        |
| **Gallery Listing**     |                             |           |        |        |           |
| Gallery Endpoint        | GET /api/photos/gallery     | ✅         | ❌      | ❌      | 🔴        |
| Filter Support          | Date, warehouse, status     | ✅         | ❌      | ❌      | 🔴        |
| Pagination              | LIMIT 50 OFFSET 0           | ✅         | ❌      | ❌      | 🔴        |
| Thumbnail Display       | Lazy loading grid           | ✅         | ❌      | ❌      | 🔴        |
| Presigned URLs          | TTL 1h for thumbnails       | ✅         | ❌      | ❌      | 🔴        |
| **Photo Detail**        |                             |           |        |        |           |
| Detail Endpoint         | GET /api/photos/{id}        | ✅         | ❌      | ❌      | 🔴        |
| Original Image          | Display processed image     | ✅         | ❌      | ❌      | 🔴        |
| Detections View         | Show detection results      | ✅         | ❌      | ❌      | 🔴        |
| History Tracking        | Show past operations        | ✅         | ❌      | ❌      | 🔴        |
| **Error Recovery**      |                             |           |        |        |           |
| Error Modal             | Show error type + details   | ✅         | ❌      | ❌      | 🔴        |
| Fix Instructions        | Guide user to resolve       | ✅         | ❌      | ❌      | 🔴        |
| Reprocess Endpoint      | POST /photos/{id}/reprocess | ✅         | ❌      | ❌      | 🔴        |
| **TOTAL PHOTO GALLERY** |                             | **6 sub** | 30%    | ⛔      | 🔴        |

---

## 3. MANUAL STOCK INITIALIZATION

| Componente            | Descripción                  | Diagrama  | Código | Estado | Prioridad |
|-----------------------|------------------------------|-----------|--------|--------|-----------|
| Form Entry            | Fill location, product, qty  | ✅         | ✅      | ✅      | 🟢        |
| Validation            | Check fields, quantities     | ✅         | ✅      | ✅      | 🟢        |
| Endpoint              | POST /api/stock/manual       | ✅         | ✅      | ✅      | 🟢        |
| Location Check        | SELECT storage_location      | ✅         | ✅      | ✅      | 🟢        |
| Config Query          | SELECT config for location   | ✅         | ✅      | ✅      | 🟢        |
| Product Validation    | Check product-config match   | ✅         | ✅      | ✅      | 🟢        |
| Packaging Validation  | Check packaging-config match | ✅         | ✅      | ✅      | 🟢        |
| Movement Create       | INSERT stock_movements       | ✅         | ✅      | ✅      | 🟢        |
| Batch Create          | INSERT stock_batch           | ✅         | ✅      | ✅      | 🟢        |
| Batch Code Gen        | LOC-PROD-DATE-SEQ            | ✅         | ✅      | ✅      | 🟢        |
| Link Movement         | UPDATE movement.batch_id     | ✅         | ✅      | ✅      | 🟢        |
| Transaction           | COMMIT/ROLLBACK              | ✅         | ✅      | ✅      | 🟢        |
| Response              | Return 201 Created           | ✅         | ✅      | ✅      | 🟢        |
| **TOTAL MANUAL INIT** |                              | **1 sub** | 95%    | ✅      | 🟢        |

---

## 4. STOCK MOVEMENTS (Plantado/Transplante/Muerte)

| Componente             | Descripción                      | Diagrama  | Código | Estado | Prioridad |
|------------------------|----------------------------------|-----------|--------|--------|-----------|
| **Shared**             |                                  |           |        |        |           |
| Endpoint               | POST /api/stock/movements        | ✅         | ✅      | ✅      | 🟢        |
| Type Router            | Route by movement_type           | ✅         | ✅      | ✅      | 🟢        |
| Validation             | Common checks (location, qty)    | ✅         | ✅      | ✅      | 🟢        |
| **PLANTADO Path**      |                                  |           |        |        |           |
| Get Location           | SELECT storage_location          | ✅         | ✅      | ✅      | 🟢        |
| Find/Create Bin        | Check or create bin              | ✅         | ✅      | ✅      | 🟢        |
| Create Movement        | INSERT IN movement               | ✅         | ✅      | ✅      | 🟢        |
| Find/Create Batch      | Check or create batch            | ✅         | ✅      | ✅      | 🟢        |
| Batch Code Gen         | LOC-PROD-DATE-SEQ                | ✅         | ✅      | ✅      | 🟢        |
| Update Batch           | quantity_current += qty          | ✅         | ✅      | ✅      | 🟢        |
| Link Movement          | batch_id = new batch             | ✅         | ✅      | ✅      | 🟢        |
| **TRANSPLANTE Path**   |                                  |           |        |        |           |
| Find Source Bin        | SELECT from source location      | ✅         | ✅      | ✅      | 🟢        |
| Find Source Batch      | Find matching batch              | ✅         | ✅      | ✅      | 🟢        |
| Qty Validation         | Check sufficient stock           | ✅         | ⚠️     | ⚠️     | 🟡        |
| Create Out Movement    | INSERT OUT movement (qty < 0)    | ✅         | ✅      | ✅      | 🟢        |
| Update Source          | quantity_current -= qty          | ✅         | ✅      | ✅      | 🟢        |
| Check Empty            | If qty = 0, deactivate           | ✅         | ⚠️     | ⚠️     | 🟡        |
| Find/Create Dest Bin   | For destination location         | ✅         | ✅      | ✅      | 🟢        |
| Create In Movement     | INSERT IN movement (qty > 0)     | ✅         | ✅      | ✅      | 🟢        |
| Find/Create Dest Batch | At destination                   | ✅         | ✅      | ✅      | 🟢        |
| Update Dest            | quantity_current += qty          | ✅         | ✅      | ✅      | 🟢        |
| Link Movements         | Connect OUT + IN                 | ✅         | ✅      | ✅      | 🟢        |
| **MUERTE Path**        |                                  |           |        |        |           |
| Find Batch             | SELECT matching batch            | ✅         | ✅      | ✅      | 🟢        |
| Qty Validation         | Check sufficient                 | ✅         | ⚠️     | ⚠️     | 🟡        |
| Create Movement        | INSERT movement (qty < 0)        | ✅         | ✅      | ✅      | 🟢        |
| Update Batch           | quantity_current -= qty          | ✅         | ✅      | ✅      | 🟢        |
| Update Empty           | quantity_empty_containers += qty | ✅         | ⚠️     | ⚠️     | 🟡        |
| Check Batch Empty      | If qty = 0, deactivate           | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Verification**       |                                  |           |        |        |           |
| FK Checks              | Validate all FKs                 | ✅         | ⚠️     | ⚠️     | 🟡        |
| Consistency Check      | Sum movements = batch qty        | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Rollback**           |                                  |           |        |        |           |
| Partial Rollback       | Delete related records           | ✅         | ⚠️     | ⚠️     | 🟡        |
| Error Logging          | Log full error + context         | ✅         | ✅      | ✅      | 🟢        |
| **TOTAL MOVEMENTS**    |                                  | **1 sub** | 85%    | ⚠️     | 🟡        |

---

## 5. STORAGE LOCATION CONFIG

| Componente        | Descripción                     | Diagrama  | Código | Estado | Prioridad |
|-------------------|---------------------------------|-----------|--------|--------|-----------|
| **Update Path**   |                                 |           |        |        |           |
| Update Form       | Pre-fill current values         | ✅         | ✅      | ✅      | 🟢        |
| Validation        | product-packaging match         | ✅         | ✅      | ✅      | 🟢        |
| Confirmation      | Warn about current stock impact | ✅         | ✅      | ✅      | 🟢        |
| Execute Update    | UPDATE storage_location_config  | ✅         | ✅      | ✅      | 🟢        |
| **Create Path**   |                                 |           |        |        |           |
| Create Form       | New config dialog               | ✅         | ✅      | ✅      | 🟢        |
| Validation        | Prevent duplicate of current    | ✅         | ⚠️     | ⚠️     | 🟡        |
| Begin Transaction | START TRANSACTION               | ✅         | ✅      | ✅      | 🟢        |
| Deactivate Old    | SET active=false on old config  | ✅         | ✅      | ✅      | 🟢        |
| Insert New        | INSERT new config active=true   | ✅         | ✅      | ✅      | 🟢        |
| Commit            | COMMIT TRANSACTION              | ✅         | ✅      | ✅      | 🟢        |
| **History**       |                                 |           |        |        |           |
| Historical Data   | Old config remains accessible   | ✅         | ⚠️     | ⚠️     | 🟡        |
| Audit Log         | Record who changed what when    | ✅         | ❌      | ❌      | 🔴        |
| **TOTAL CONFIG**  |                                 | **4 sub** | 80%    | ⚠️     | 🟡        |

---

## 6. ANALYTICS SYSTEM

| Componente           | Descripción                     | Diagrama  | Código | Estado | Prioridad |
|----------------------|---------------------------------|-----------|--------|--------|-----------|
| **Manual Filtering** |                                 |           |        |        |           |
| Filter UI            | Select warehouse, area, product | ✅         | ⚠️     | ⚠️     | 🟡        |
| SQL Builder          | Build query from filters        | ✅         | ✅      | ✅      | 🟢        |
| Query Exec           | Execute on database             | ✅         | ✅      | ✅      | 🟢        |
| Visualization        | Charts (backend or frontend)    | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Sales Comparison** |                                 |           |        |        |           |
| CSV Upload           | POST /api/analytics/upload-csv  | ✅         | ❌      | ❌      | 🔴        |
| CSV Parse            | Validate + parse CSV            | ✅         | ❌      | ❌      | 🔴        |
| Stock Query          | Query current active stock      | ✅         | ❌      | ❌      | 🔴        |
| Variance Calc        | current_stock - sales           | ✅         | ❌      | ❌      | 🔴        |
| Report Gen           | Generate comparison report      | ✅         | ❌      | ❌      | 🔴        |
| **AI Analytics**     |                                 |           |        |        |           |
| NL Query Input       | Accept natural language         | ✅         | ❌      | ❌      | 🔴        |
| LLM Processing       | Call OpenAI/compatible API      | ✅         | ❌      | ❌      | 🔴        |
| SQL Generation       | Generate + validate SQL         | ✅         | ❌      | ❌      | 🔴        |
| Query Execute        | Run with timeout 30s            | ✅         | ❌      | ❌      | 🔴        |
| Chart Generation     | Python (matplotlib/seaborn)     | ✅         | ❌      | ❌      | 🔴        |
| **Export**           |                                 |           |        |        |           |
| Excel Export         | Format + download               | ✅         | ❌      | ❌      | 🔴        |
| CSV Export           | Raw data export                 | ✅         | ❌      | ❌      | 🔴        |
| **TOTAL ANALYTICS**  |                                 | **5 sub** | 25%    | ⛔      | 🔴        |

---

## 7. PRICE LIST MANAGEMENT

| Componente           | Descripción               | Diagrama  | Código | Estado | Prioridad |
|----------------------|---------------------------|-----------|--------|--------|-----------|
| **Packaging CRUD**   |                           |           |        |        |           |
| Create Packaging     | POST /packaging           | ✅         | ⚠️     | ⚠️     | 🟡        |
| Read Packaging       | GET /packaging, filtering | ✅         | ⚠️     | ⚠️     | 🟡        |
| Update Packaging     | PUT /packaging/{id}       | ✅         | ⚠️     | ⚠️     | 🟡        |
| Delete Packaging     | DELETE /packaging/{id}    | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Product CRUD**     |                           |           |        |        |           |
| Category CRUD        | Create/Read/Update/Delete | ✅         | ✅      | ✅      | 🟢        |
| Family CRUD          | Create/Read/Update/Delete | ✅         | ✅      | ✅      | 🟢        |
| Product CRUD         | Create/Read/Update/Delete | ✅         | ✅      | ✅      | 🟢        |
| **Price List**       |                           |           |        |        |           |
| Select Combo         | Product + Packaging       | ✅         | ⚠️     | ⚠️     | 🟡        |
| Price Entry          | Wholesale + retail prices | ✅         | ⚠️     | ⚠️     | 🟡        |
| Auto Calc            | total_per_box calculation | ✅         | ⚠️     | ⚠️     | 🟡        |
| Validation           | retail >= wholesale       | ✅         | ⚠️     | ⚠️     | 🟡        |
| Save to DB           | INSERT/UPDATE price_list  | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Bulk Operations**  |                           |           |        |        |           |
| Bulk Price Update    | Increase/decrease by %    | ✅         | ❌      | ❌      | 🔴        |
| Bulk Availability    | Change status en masa     | ✅         | ❌      | ❌      | 🔴        |
| Bulk Discount        | Apply discount %          | ✅         | ❌      | ❌      | 🔴        |
| Preview Changes      | Show before/after         | ✅         | ❌      | ❌      | 🔴        |
| Execute Batch        | Transaction UPDATE        | ✅         | ❌      | ❌      | 🔴        |
| Notify & Log         | Audit trail creation      | ✅         | ❌      | ❌      | 🔴        |
| **TOTAL PRICE LIST** |                           | **5 sub** | 65%    | ⚠️     | 🟡        |

---

## 8. MAP WAREHOUSE VIEWS

| Componente            | Descripción                         | Diagrama  | Código | Estado | Prioridad |
|-----------------------|-------------------------------------|-----------|--------|--------|-----------|
| **Level 1: Overview** |                                     |           |        |        |           |
| Bulk Load             | GET /map/bulk-load (single call)    | ✅         | ❌      | ❌      | 🔴        |
| Map View              | PostGIS warehouse polygons          | ✅         | ⚠️     | ⚠️     | 🟡        |
| Summary Metrics       | Count warehouses, areas, errors     | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Level 2: Internal** |                                     |           |        |        |           |
| Warehouse Drill       | Click warehouse polygon             | ✅         | ✅      | ✅      | 🟢        |
| Storage Areas         | Show canteros within warehouse      | ✅         | ✅      | ✅      | 🟢        |
| Filter by Cantero     | N/S/E/W/C filter                    | ✅         | ✅      | ✅      | 🟢        |
| Preview Cards         | Grid of locations                   | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Level 3: Detail**   |                                     |           |        |        |           |
| Detail Endpoint       | GET /storage-locations/{id}/detail  | ✅         | ❌      | ❌      | 🔴        |
| Processed Image       | ML processed visualization          | ✅         | ❌      | ❌      | 🔴        |
| Detections            | Show detected items                 | ✅         | ❌      | ❌      | 🔴        |
| Financial Data        | Cost + potential value              | ✅         | ❌      | ❌      | 🔴        |
| Maceta Distribution   | Breakdown by size                   | ✅         | ❌      | ❌      | 🔴        |
| Quality Metrics       | Health score + growth               | ✅         | ❌      | ❌      | 🔴        |
| **Level 4: History**  |                                     |           |        |        |           |
| History Endpoint      | GET /storage-locations/{id}/history | ✅         | ❌      | ❌      | 🔴        |
| Period Details        | 3-month periods                     | ✅         | ❌      | ❌      | 🔴        |
| Timeline Chart        | Line chart quantity trends          | ✅         | ❌      | ❌      | 🔴        |
| Movement Breakdown    | Plantado, transplante, muerte       | ✅         | ❌      | ❌      | 🔴        |
| **Database Layer**    |                                     |           |        |        |           |
| MV Warehouse          | mv_warehouse_summary                | ✅         | ❌      | ❌      | 🔴        |
| MV Preview            | mv_storage_location_preview         | ✅         | ❌      | ❌      | 🔴        |
| MV History            | mv_storage_location_history         | ✅         | ❌      | ❌      | 🔴        |
| PostGIS Polygons      | Warehouse boundaries                | ✅         | ⚠️     | ⚠️     | 🟡        |
| **Cache Layer**       |                                     |           |        |        |           |
| Redis Cache           | Bulk, Detail, History caches        | ✅         | ⚠️     | ⚠️     | 🟡        |
| Cache TTL             | 10min, 1h, 1day                     | ✅         | ❌      | ❌      | 🔴        |
| **TOTAL MAP VIEWS**   |                                     | **6 sub** | 35%    | ⛔      | 🔴        |

---

## RESUMEN CONSOLIDADO

### Por Severidad

| Severidad         | Flujo           | Componentes | % Impl | Bloqueantes         |
|-------------------|-----------------|-------------|--------|---------------------|
| 🔴 **CRÍTICO**    | ML Pipeline     | 9/22        | 40%    | 5 child tasks       |
| 🔴 **CRÍTICO**    | Photo Gallery   | 2/16        | 30%    | 10 gallery + detail |
| 🔴 **CRÍTICO**    | Analytics       | 2/19        | 25%    | 12 features         |
| 🔴 **CRÍTICO**    | Map Views       | 4/24        | 35%    | 14 features         |
| 🟡 **IMPORTANTE** | Stock Movements | 25/32       | 85%    | 3 validations       |
| 🟡 **IMPORTANTE** | Location Config | 10/14       | 80%    | 1 audit log         |
| 🟡 **IMPORTANTE** | Price List      | 9/21        | 65%    | 6 bulk ops          |
| 🟢 **OK**         | Manual Init     | 13/13       | 95%    | 0                   |

### Totales

- **Total Diagramas**: 38
- **Total Componentes**: 167
- **Implementados**: 85 (51%)
- **Parciales**: 32 (19%)
- **Faltantes**: 50 (30%)
- **Bloqueantes Críticos**: 37

---

## ARCHIVOS CRÍTICOS A REVISAR/CREAR

| Archivo                                      | Estado        | Acción                                  |
|----------------------------------------------|---------------|-----------------------------------------|
| `app/services/photo/detection_service.py`    | ❌ VACÍO       | Implementar child tasks (SAHI + Direct) |
| `app/controllers/analytics_controller.py`    | ⚠️ Incompleto | Agregar CSV upload + export             |
| `app/services/photo/photo_upload_service.py` | ⚠️ Incompleto | Agregar callback + polling              |
| Materialized Views                           | ❌ NO EXISTEN  | Crear 3 MVs en DB                       |
| Gallery Endpoints                            | ❌ NO EXISTEN  | Crear 5 endpoints gallery               |
| Map Endpoints                                | ⚠️ Parcial    | Crear bulk-load + detail + history      |

---
