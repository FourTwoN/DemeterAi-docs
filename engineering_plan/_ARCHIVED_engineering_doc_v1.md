# Engineering Plan \- Automated Cactus and Succulent Counting System

## 1\. Context and Project Objective

This application aims to automate the counting of cacti and succulents in a cultivation of over
600,000 plants using Machine Learning. Currently, stock tracking is performed manually and
infrequently. The proposed solution allows users to input photos of the cultivation, process them
with detection and segmentation models (YOLO v11), and obtain accurate counts organized by
geographic location.

### Main Technologies

- **Language**: Python 3.12
- **Web Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Database**: PostgreSQL \+ PostGIS for geo coordinates
- **Async Processing**: Celery \+ Redis
- **Machine Learning**: YOLO v11 (segmentation and detection)
- **Containers**: Docker \+ Docker Compose

---

## 2\. Database Architecture

### 2.0 Mermaid diagram

\---

config:

theme: redux-dark-color

layout: elk

\---

erDiagram

    warehouses ||--o{ storage\_areas : "contains"

    storage\_areas ||--o{ storage\_locations : "contains"

    storage\_locations ||--o{ storage\_bins : "contains"

    storage\_bin\_types ||--o{ storage\_bins : "defines"

    warehouses {

        int id PK

        varchar code UK

        varchar name

        varchar type "greenhouse|shadehouse|open\_field|tunnel"

        geometry geojson\_coordinates "PostGIS"

        geometry centroid "PostGIS"

        numeric area\_m2 "GENERATED ST\_Area(geojson\_coordinates::geography)"

        boolean active "default true"

        timestamp created\_at

        timestamp updated\_at

    }

    storage\_areas {

        int id PK

        int warehouse\_id FK

        varchar code UK

        varchar name

        varchar position "N|S|E|W|C"

        geometry geojson\_coordinates "PostGIS"

        geometry centroid "PostGIS"

        numeric area\_m2 "GENERATED ST\_Area(geojson\_coordinates::geography)"

        boolean active "default true"

        timestamp created\_at

        timestamp updated\_at

    }

    storage\_locations {

        int id PK

        int storage\_area\_id FK

        varchar code UK

        varchar qr\_code UK

        varchar name

        text description

        geometry geojson\_coordinates "PostGIS"

        geometry centroid "PostGIS"

        numeric area\_m2 "GENERATED ST\_Area(geojson\_coordinates::geography)"

        boolean active "default true"

        timestamp created\_at

        timestamp updated\_at

    }

    storage\_bin\_types {

        int id PK

        varchar code UK

        varchar name

        varchar category "plug|seedling\_tray|box|segment|pot"

        text description

        int rows "nullable"

        int columns "nullable"

        int capacity "nullable"

        numeric length\_cm "nullable"

        numeric width\_cm "nullable"

        numeric height\_cm "nullable"

        boolean is\_grid "nullable"

        timestamp created\_at

        timestamp updated\_at

    }

    storage\_bins {

        int id PK

        int storage\_location\_id FK

        int storage\_bin\_type\_id FK

        int photo\_session\_id FK "NEW \- links to session"

        varchar code UK

        varchar label

        text description

        jsonb position\_metadata "segmentation\_mask, bbox, confidence"

        varchar status "active|maintenance|retired"

        timestamp created\_at

    }

    product\_categories ||--o{ product\_families : "groups"

    product\_families ||--o{ products : "contains"

    product\_categories {

        int id PK

        varchar code UK

        varchar name

        text description

    }

    product\_families {

        int id PK

        int category\_id FK

        varchar name

        varchar scientific\_name

        text description

    }

    products {

        int id PK

        int family\_id FK

        varchar sku UK

        varchar common\_name

        varchar scientific\_name

        text description

        jsonb custom\_attributes

    }

    product\_states {

        int id PK

        varchar code UK

        varchar name

        text description

        boolean is\_sellable "default false"

        int sort\_order

    }

    product\_sizes {

        int id PK

        varchar code UK

        varchar name

        text description

        numeric min\_height\_cm

        numeric max\_height\_cm

        numeric price\_factor "default 1.0"

        int sort\_order

    }

    packaging\_types ||--o{ packaging\_catalog : "defines"

    packaging\_materials ||--o{ packaging\_catalog : "defines"

    packaging\_colors ||--o{ packaging\_catalog : "defines"

    packaging\_types {

        int id PK

        varchar code UK

        varchar name

        text description

        numeric price\_factor "default 1.0"

    }

    packaging\_materials {

        int id PK

        varchar code UK

        varchar name

        text description

    }

    packaging\_colors {

        int id PK

        varchar name UK

        varchar hex\_code

        numeric price\_factor "default 1.0"

    }

    packaging\_catalog {

        int id PK

        int packaging\_type\_id FK

        int packaging\_material\_id FK

        int packaging\_color\_id FK

        varchar sku UK

        varchar name

        numeric volume\_liters

        numeric diameter\_cm

        numeric height\_cm

        numeric unit\_price

    }

    storage\_bins ||--o{ stock\_batches : "stores"

    products ||--o{ stock\_batches : "product\_of"

    product\_states ||--o{ stock\_batches : "state\_of"

    product\_sizes ||--o{ stock\_batches : "size\_of"

    packaging\_catalog ||--o{ stock\_batches : "packaged\_in"

    stock\_batches ||--o{ stock\_movements : "has\_movements"

    users ||--o{ stock\_movements : "performs"

    storage\_bins ||--o{ stock\_movements : "source\_bin"

    storage\_bins ||--o{ stock\_movements : "destination\_bin"

    photo\_processing\_sessions ||--o{ stock\_movements : "generated\_by"

    stock\_batches {

        int id PK

        varchar batch\_code UK

        int current\_storage\_bin\_id FK

        int product\_id FK

        int product\_state\_id FK

        int product\_size\_id FK "nullable"

        boolean has\_packaging "default false"

        int packaging\_catalog\_id FK "nullable"

        int quantity\_initial "CHECK \>= 0"

        int quantity\_current "CHECK \>= 0"

        int quantity\_empty\_containers "default 0"

        numeric quality\_score "0-5"

        date planting\_date "nullable"

        date germination\_date "nullable"

        date transplant\_date "nullable"

        date expected\_ready\_date "nullable"

        text notes

        jsonb custom\_attributes

        timestamp created\_at

        timestamp updated\_at

    }

    stock\_movements {

        int id PK

        uuid movement\_id UK

        int batch\_id FK

        varchar movement\_type "plantar|sembrar|transplante|muerte|ventas|foto|ajuste"

        int source\_bin\_id FK "nullable"

        int destination\_bin\_id FK "nullable"

        int quantity "CHECK \!= 0"

        int user\_id FK

        numeric unit\_price "KEEP for COGS"

        numeric total\_price "nullable"

        text reason\_description

        int processing\_session\_id FK "nullable"

        varchar source\_type "manual|ia"

        boolean is\_inbound "ingreso or egreso"

        timestamp created\_at

    }

    s3\_images ||--o{ photo\_processing\_sessions : "references"

    s3\_images ||--o{ product\_sample\_images : "references"

    s3\_images {

        int id PK

        uuid image\_id UK

        varchar s3\_bucket

        varchar s3\_key\_original UK

        varchar s3\_key\_thumbnail

        varchar content\_type "image/jpeg|image/png"

        bigint file\_size\_bytes

        int width\_px

        int height\_px

        jsonb exif\_metadata

        jsonb gps\_coordinates

        varchar upload\_source "web|mobile|api"

        int uploaded\_by\_user\_id FK

        varchar status "uploaded|processing|ready|failed"

        text error\_details "NEW \- for failures"

        timestamp processing\_status\_updated\_at "NEW"

        timestamp created\_at

        timestamp updated\_at

    }

    storage\_locations ||--o{ photo\_processing\_sessions : "processed\_in"

    photo\_processing\_sessions ||--o{ detections : "contains"

    photo\_processing\_sessions ||--o{ estimations : "contains"

    users ||--o{ photo\_processing\_sessions : "validates"

    stock\_movements ||--o{ detections : "created\_by"

    stock\_movements ||--o{ estimations : "created\_by"

    photo\_processing\_sessions {

        int id PK

        uuid session\_id UK

        int storage\_location\_id FK "nullable"

        int original\_image\_id FK "s3\_images"

        int processed\_image\_id FK "s3\_images"

        int total\_detected

        int total\_estimated

        int total\_empty\_containers

        numeric avg\_confidence

        jsonb category\_counts

        varchar status "pending|processing|completed|failed"

        text error\_message

        boolean validated "default false"

        int validated\_by\_user\_id FK

        timestamp validation\_date

        jsonb manual\_adjustments

        timestamp created\_at

        timestamp updated\_at

    }

    classifications ||--o{ detections : "classifies"

    classifications ||--o{ estimations : "classifies"

    detections {

        int id PK

        int session\_id FK

        int stock\_movement\_id FK

        int classification\_id FK

        numeric center\_x\_px "renamed from x\_coord\_px"

        numeric center\_y\_px "renamed from y\_coord\_px"

        int width\_px "renamed from bbox\_width\_px"

        int height\_px "renamed from bbox\_height\_px"

        numeric area\_px "GENERATED width\_px \* height\_px"

        jsonb bbox\_coordinates "x1,y1,x2,y2"

        numeric detection\_confidence "renamed from category\_confidence"

        boolean is\_empty\_container "default false"

        boolean is\_alive "default true"

        timestamp created\_at

    }

    estimations {

        int id PK

        int session\_id FK

        int stock\_movement\_id FK

        int classification\_id FK

        jsonb vegetation\_polygon

        numeric detected\_area\_cm2

        int estimated\_count

        varchar calculation\_method "band\_estimation|density\_estimation|grid\_analysis"

        numeric estimation\_confidence "default 0.70"

        boolean used\_density\_parameters

        timestamp created\_at

    }

    products ||--o{ classifications : "species"

    product\_sizes ||--o{ classifications : "size"

    packaging\_catalog ||--o{ classifications : "pot\_type"

    classifications {

        int id PK

        int product\_id FK

        int product\_size\_id FK "nullable"

        int packaging\_catalog\_id FK "nullable"

        int product\_conf "NEW \- product classification confidence"

        int packaging\_conf "NEW \- packaging classification confidence"

        int product\_size\_conf "NEW \- size classification confidence"

        varchar model\_version "NEW \- ML model version"

        varchar name

        text description

        timestamp created\_at

    }

    products ||--o{ product\_sample\_images : "has\_samples"

    product\_states ||--o{ product\_sample\_images : "state\_at\_capture"

    product\_sizes ||--o{ product\_sample\_images : "size\_at\_capture"

    storage\_locations ||--o{ product\_sample\_images : "captured\_at"

    users ||--o{ product\_sample\_images : "captured\_by"

    product\_sample\_images {

        int id PK

        int product\_id FK

        int image\_id FK "s3\_images"

        int product\_state\_id FK "nullable"

        int product\_size\_id FK "nullable"

        int storage\_location\_id FK "nullable"

        varchar sample\_type "reference|growth\_stage|quality\_check|monthly\_sample"

        date capture\_date

        int captured\_by\_user\_id FK

        text notes

        int display\_order

        boolean is\_primary

        timestamp created\_at

    }

    storage\_locations ||--o{ storage\_location\_config : "configured\_with"

    products ||--o{ storage\_location\_config : "grows"

    packaging\_catalog ||--o{ storage\_location\_config : "uses"

    product\_states ||--o{ storage\_location\_config : "expected\_state"

    storage\_bin\_types ||--o{ density\_parameters : "calibrated\_for"

    products ||--o{ density\_parameters : "calibrated\_for"

    packaging\_catalog ||--o{ density\_parameters : "calibrated\_for"

    storage\_location\_config {

        int id PK

        int storage\_location\_id FK

        int product\_id FK

        int packaging\_catalog\_id FK "nullable"

        int expected\_product\_state\_id FK

        numeric area\_cm2

        boolean active "default true"

        text notes

        timestamp created\_at

        timestamp updated\_at

    }

    density\_parameters {

        int id PK

        int storage\_bin\_type\_id FK

        int product\_id FK

        int packaging\_catalog\_id FK

        numeric avg\_area\_per\_plant\_cm2

        numeric plants\_per\_m2

        numeric overlap\_adjustment\_factor "default 0.85"

        numeric avg\_diameter\_cm

        text notes

        timestamp created\_at

        timestamp updated\_at

    }

    users {

        int id PK

        varchar email UK

        varchar password\_hash

        varchar first\_name

        varchar last\_name

        varchar role "admin|supervisor|worker|viewer"

        boolean active "default true"

        timestamp last\_login

        timestamp created\_at

        timestamp updated\_at

    }

### 2.1. Location Hierarchy

The database is organized around the concept of geographic location:

**Warehouses** (Largest unit)

- Represent greenhouses, tunnels, or shadehouses
- Contain geographic coordinates that form a rectangle on the map
- Have relationships with Storage Areas

**Storage Areas**

- Subdivide a warehouse (generally North or South)
- Contain rectangular geographic coordinates
- Have relationships with Storage Locations

**Storage Locations** (Minimum unit)

- Space between column and column of a greenhouse
- Contain rectangular geographic coordinates
- The unit where each photo is taken
- Have an associated configuration table (StorageLocationConfig)

### 2.2. Cultivation Zones

Storage bins represent different container types where cacti/succulents can be:

1. **Plugs**: Black trays with small holes where seeds are placed, not ready for sale
2. **Seedling Trays**: Boxes with soil where cacti are planted to develop roots, not ready for sale
3. **Segments**: Cacti planted in pots in rectangular grid form, ready for sale
4. **Boxes**: Boxes with cacti already in pots (different from seedling trays), ready for sale

Storage bins are defined by their `storage_bin_type`, which specifies the category (plug,
seedling\_tray, box, segment, pot).

### 2.3. Data Flow in the Database for ML path

Photo → PhotoProcessingSession → Detections \+ Estimations → StockMovement → StockBatch

**PhotoProcessingSession**

- Saves the original photo
- Capture date
- Relevant metadata

**Detections**

- Individual detections made by YOLO v11
- Bounding box coordinates

**Estimations**

- Plants that could not be detected individually
- Estimation based on area and pot size

**StockMovement**

- Records stock transactions
- Count date
- User who performed it
- Can be automatic receipt (from photo) or manual (by worker):

**StockBatch**

- Groups individual detections into categories
- Attributes: packaging, size, product, price, state, etc.
- Example: 1500 large plants \+ 500 medium plants from the same segment

### 2.4. Data Flow in the Database for Manual Path

Manual Input → StockMovement → StockBatch

Manual Input can be INGRESS or EGRESS. Egress may be for death, sell, transplant (plant grew too
big) and other.

DATA FLOW MES A MES:

1\. Cada foto a final de mes se marca como el inicio del stock de ese mes, ese stock puede sufrir
variaciones por:

\- Muertes (resta) (plug, almacigo, cajones y segmento)
\- Plantado (suma) (cajones y segmentos)
\- Trasplante (resta en un claro, suma en otro): plug \-\> almacigo \-\> cajon/segmento (tamano
chico) \-\> cajon/segmento (tamano mediano) \-\> cajon/segmento (tamano grande)

2\. AHORA, a final del siguiente MES se toma otra foto y si faltan PLANTAS se consideran VENTAS (
solo para cajon/segmento). ADEMAS, puede haber una especie de validacion externa gracias a ventas de
parte de CLIENTE (CSV lo mas probable) donde indica cantidad, clasificacion, tipo\_maceta \+ color
PERO DATOS GEOGRAFICOS NO

CON esa siguiente foto se hace ese calculo e inicia EL SIGUIENTE historial y se reinicia de nuevo el
proceso 1

2.4. Complementary Tables

- **Users**: Administrators or workers
- **Products**: Catalog of cactus/succulent species
- **PackagingCatalog**: Types of packaging with their prices
- **StorageLocationConfig**: Information loaded by administrator about what is planted in each
  storage location

### 2.5. PostgreSQL Considerations

- Use PostgreSQL method to verify if a point (latitude, longitude) falls within a coordinate polygon
- Many Foreign Keys and complex relationships
- The database is NOT changed, SQLAlchemy is adapted to it

---

## 3\. Repository Layer

### 3.1. Responsibility

Repositories are the **only layer** that directly accesses the database. They handle:

- Data access
- Updates (UPDATE)
- Inserts (INSERT)
- Queries (SELECT)
- Deletions (DELETE)

### 3.2. Technology

**SQLAlchemy** for:

- Simplifying data access
- Automatic connection handling
- Optimized queries
- Easier updates and inserts

### 3.3. Structure

/repositories

/models \# SQLAlchemy models (exact database representation)

base\_repo.py \# Base repository with common definitions

warehouse\_repo.py

storage\_area\_repo.py

storage\_location\_repo.py

storage\_bin\_repo.py

storage\_bin\_type\_repo.py

photo\_processing\_session\_repo.py

stock\_movement\_repo.py

stock\_batch\_repo.py

product\_repo.py

product\_category\_repo.py

product\_family\_repo.py

packaging\_catalog\_repo.py

packaging\_type\_repo.py

packaging\_material\_repo.py

packaging\_color\_repo.py

storage\_location\_config\_repo.py

density\_parameters\_repo.py

user\_repo.py

detection\_repo.py

estimation\_repo.py

product\_state\_repo.py

product\_size\_repo.py

### 3.4. Design Principles

- **Single Responsibility**: Each repository handles one main entity
- **Reuse**: Repositories can call other repositories to avoid duplication
- **Simplicity vs. Completeness**:
    - Simple tables (like Products) don't need super-repositories
    - Complex tables (like StockBatch, StockMovement) need robust methods
- **Base Repo**: Contains basic CRUD operations, others inherit and extend
- **Models**: Must be identical to the database structure

### 3.5. SQLAlchemy Considerations

- **Avoid infinite loops** with circular relationships
- **Lazy vs Eager Loading**: Know when to load relationships
- **Don't fetch unnecessary information**: Optimize queries as needed
- Be careful with multiple Foreign Keys
- Connections MUST be through Singleton

---

## 4\. Service Layer

### 4.1. Responsibility

Services are the **middle layer** between controllers and repositories. They coordinate business
logic.

### 4.2. Main Functions

- Receive Pydantic schemas from controllers
- Transform schemas to SQLAlchemy models
- Call other services (not directly to foreign repositories)
- Call their own repository
- Coordinate complex operations

### 4.3. Communication Rule

Controller → Service A → Service B → Repository B

                      ↓

                 Repository A

NOT ALLOWED:

Service A → Repository B directly (must call Service B)

### 4.4. Structure

/services

base\_service.py

warehouse\_service.py

storage\_area\_service.py

storage\_location\_service.py

storage\_bin\_service.py

photo\_processing\_session\_service.py

stock\_movement\_service.py

stock\_batch\_service.py

product\_service.py

packaging\_catalog\_service.py

storage\_location\_config\_service.py

user\_service.py

/ml\_processing \# Machine Learning Pipeline

    pipeline\_coordinator.py    \# Main pipeline orchestrator

    localization\_service.py

    segmentation\_service.py

    detection\_service.py

    estimation\_service.py

    image\_processing\_service.py

### 4.5. Basic Methods

Each service should have at least:

- `get_one(id)`: Get an entity by ID
- `get_all()`: List all entities
- `update(id, data)`: Update an entity
- `create(data)`: Create new entity
- `delete(id)`: Delete existing entity
- Specific methods according to business needs

---

## 5\. Machine Learning Pipeline

### 5.1. Integration with API

**CRITICAL**: The pipeline is NOT separated from the REST API. It's an integral part of the system
and must:

- Use the same services
- Use the same repositories
- Follow the same conventions
- Be organized within `/services/ml_processing`

### 5.2. Complete Pipeline Flow

#### Step 1: Reception and Localization

1. Receive photo
2. Extract metadata (GPS coordinates)
3. Search corresponding storage location via PostgreSQL query (point within polygon)
4. If no location: mark as "no location" or assign to "undefined" storage location

#### Step 2: Segmentation

1. Pass complete photo through YOLO v11 segmentation model
2. Identify important areas (plugs, boxes, segments)
3. Smooth obtained masks
4. Fill internal holes in masks
5. Crop images according to masks with original quality
6. Typical result: 1 segment \+ 4 boxes (may vary)

#### Step 3A: Segment Processing

1. **SAHI Division**: Divide segment into 512x512 squares (or 640x640, configurable)
2. **Detection**: Pass each square through YOLO v11 detection
3. **Unification**: Consolidate all detections
4. **Creation of detection mask**: Form uniform and smooth mask with all bounding boxes
5. **Subtraction**: Segment mask \- Detection mask \= Remaining area
6. **Remaining area estimation**:
    - Apply OTSU with HSV to eliminate empty soil
    - Calculate pixels of remaining area
    - Estimate number of plants according to pot size (e.g., 5-7cm square pots). Pot size may be
      obtained through close by detections or configuration saved in database table
      density\_parameters

#### Step 3B: Box Processing

1. **Direct detection**: Pass complete box image through detector
2. **Estimation**: Calculate undetected plants (very full boxes)

#### Step 3C: Plug and Seedling Tray Processing

- Seedling trays are processed like boxes: detection \+ estimation
- Plugs: detection \+ estimation

#### Step 4: Configuration Association

1. Get StorageLocationConfig from identified storage location
2. Extract: product, packaging, price
3. If configuration doesn't exist: save anyway with relation to storage location (will be updated
   later with DB trigger)

#### Step 5: Final Image Generation

Create image with visualizations:

- **Detections**: Transparent circles (80% opacity) at the center of each bounding box
    - Use nice colors (not generic vibrant YOLO colors)
    - Allow seeing the cactus underneath
    - Occupy 80% of original bounding box
- **Estimated area**: Smooth and transparent mask with different color
- Save both original image and image with visualizations

#### Step 6: Database Persistence

1. Insert into `PhotoProcessingSession`
2. Insert detections into `Detections`
3. Insert estimations into `Estimations`
4. Create record in `StockMovement`
5. Group and create records in `StockBatch`

### 5.3. Configuration

Configurable parameters:

- SAHI square size (512x512 or 640x640)
- Confidence threshold for detections
- Pot sizes for estimation (section\_id \-\> pot\_id \-\> density\_parameters)
- Visualization colors
- Mask smoothing level

### 5.4. Class Structure

\# Conceptual example (DO NOT copy literally)

class PipelineCoordinator:

    """Orchestrates the entire pipeline"""

    def process\_photo(self, photo, metadata):

        \# 1\. Localization

        location \= localization\_service.find\_storage\_location(metadata)



        \# 2\. Segmentation

        masks \= segmentation\_service.segment(photo)



        \# 3\. Detection and Estimation

        for mask in masks:

            if mask.type \== 'segment':

                detections \= detection\_service.detect\_with\_sahi(mask)

                estimations \= estimation\_service.estimate\_remaining(mask, detections)

            elif mask.type in \['box', 'seedling\_tray'\]:

                detections \= detection\_service.detect\_direct(mask)

                estimations \= estimation\_service.estimate\_remaining(mask, detections)



        \# 4\. Configuration

        config \= storage\_location\_config\_service.get\_by\_location(location.id)



        \# 5\. Final image

        visualized\_image \= image\_processing\_service.create\_visualization(photo, detections, estimations)



        \# 6\. Persistence

        stock\_movement\_service.create\_from\_detection(location, detections, estimations, config)

---

## 6\. Controller Layer (Endpoints)

### 6.1. Technology

- **FastAPI** for route definition
- **Pydantic** for validation schemas
- Strong typing in all parameters and responses

### 6.2. Location Endpoints

#### GET `/api/warehouses/locations`

Get all warehouses with their geographic coordinates.

**Response:**

\[

{

    "id": 1,

    "name": "Greenhouse 15",

    "type": "greenhouse",

    "coordinates": \[\[lat1, lon1\], \[lat2, lon2\], \[lat3, lon3\], \[lat4, lon4\]\]

}

\]

#### GET `/api/warehouses/{warehouse_id}/storage-areas`

Get storage areas of a warehouse with their storage locations and preview information.

**Response:**

{

"warehouse\_id": 1,

"storage\_areas": \[

    {

      "id": 1,

      "name": "North",

      "coordinates": \[\[lat1, lon1\], \[lat2, lon2\], \[lat3, lon3\], \[lat4, lon4\]\],

      "storage\_locations": \[

        {

          "id": 1,

          "number": 1,

          "coordinates": \[\[lat1, lon1\], \[lat2, lon2\], \[lat3, lon3\], \[lat4, lon4\]\],

          "preview": {

            "packaging": "R5 golden",

            "product": "Echeveria",

            "last\_detection": {

              "date": "2025-01-15",

              "plant\_quantity": 1200

            }

          }

        }

      \]

    }

\]

}

#### GET `/api/storage-areas/{storage_area_id}`

Get an individual storage area with its storage locations.

#### GET `/api/storage-areas/{storage_area_id}/storage-locations`

Get only the storage locations of a storage area.

#### GET `/api/warehouses/{warehouse_id}/storage-locations`

Get all storage locations of a warehouse (without grouping by storage area).

#### GET `/api/storage-locations/{storage_location_id}/detail`

Get detail of the last detection of a storage location.

**Response:**

{

"storage\_location\_id": 1,

"last\_detection": {

    "date": "2025-01-15T10:30:00",

    "photo\_url": "/media/photos/location1\_20250115.jpg",

    "visualized\_photo\_url": "/media/photos/location1\_20250115\_viz.jpg",

    "total\_plants": 1200,

    "detected\_plants": 1100,

    "estimated\_plants": 100,

    "configuration": {

      "product": "Echeveria",

      "packaging": "R5 golden",

      "size": "large"

    },

    "estimated\_price": 24000.50

}

}

#### GET `/api/storage-locations/{storage_location_id}/history`

Get complete detection history of a storage location.

**Response:**

{

"storage\_location\_id": 1,

"history": \[

    {

      "date": "2025-01-15T10:30:00",

      "photo\_url": "/media/photos/location1\_20250115.jpg",

      "visualized\_photo\_url": "/media/photos/location1\_20250115\_viz.jpg",

      "total\_plants": 1200,

      "detected\_plants": 1100,

      "estimated\_plants": 100,

      "batches": \[

        {

          "quantity": 800,

          "product": "Echeveria",

          "packaging": "R5 golden",

          "size": "large",

          "unit\_price": 20.50

        },

        {

          "quantity": 400,

          "product": "Echeveria",

          "packaging": "R5 golden",

          "size": "medium",

          "unit\_price": 15.00

        }

      \]

    }

\]

}

### 6.3. Configuration Endpoints

#### GET `/api/configurations/storage-location/{storage_location_id}`

Get configuration of a specific storage location.

#### POST `/api/configurations/storage-location`

Create or update configuration of one or multiple storage locations.

**Request Body:**

{

"storage\_location\_ids": \[1, 2, 3, 4, 5\],

"configuration": {

    "product\_id": 10,

    "packaging\_id": 5,

    "notes": "Planted in January 2025"

}

}

#### GET `/api/configurations/warehouse/{warehouse_id}`

List all configurations of a warehouse.

#### GET `/api/configurations/storage-area/{storage_area_id}`

List all configurations of a storage area.

#### GET `/api/products`

List all available products (for frontend autocomplete).

#### GET `/api/packaging`

List all available packaging (for frontend autocomplete).

### 6.4. Stock Input Endpoints

#### POST `/api/stock/photo`

Upload one or multiple photos for processing.

**Behavior:**

- **Single photo**: Synchronous processing, returns immediate result with complete detail
- **Multiple photos**: Asynchronous processing with Celery, returns task IDs

**Request (single photo):**

multipart/form-data

\- photo: image file

**Response (single photo):**

{

"processing\_id": 123,

"storage\_location\_id": 5,

"result": {

    // Same format as /api/storage-locations/{storage\_location\_id}/detail

}

}

**Request (multiple photos):**

multipart/form-data

\- photos\[\]: array of image files

**Response (multiple photos):**

{

"task\_ids": \["task-uuid-1", "task-uuid-2", "task-uuid-3"\],

"total\_photos": 3,

"message": "Processing initiated. Check status with /api/stock/tasks/status"

}

#### GET `/api/stock/tasks/status`

Query status of Celery async tasks.

**Query Parameters:**

- `task_ids`: list of task IDs separated by comma

**Response:**

{

"tasks": \[

    {

      "task\_id": "task-uuid-1",

      "status": "PROCESSING",

      "progress": 45,

      "message": "Segmenting image..."

    },

    {

      "task\_id": "task-uuid-2",

      "status": "SUCCESS",

      "progress": 100,

      "result": {

        "processing\_id": 124,

        "storage\_location\_id": 6

      }

    },

    {

      "task\_id": "task-uuid-3",

      "status": "PENDING",

      "progress": 0

    }

\]

}

#### POST `/api/stock/manual`

Manual stock input by workers.

**Request Body:**

{

"storage\_location\_id": 5,

"product\_id": 10,

"packaging\_id": 5,

"quantity": 200,

"notes": "Planted today"

}

### 6.5. Analytics Endpoints

These endpoints must be robust and allow multiple filters.

#### POST `/api/analytics/report`

Generate customized report with filters.

**Request Body:**

{

"filters": {

    "warehouse\_ids": \[1, 2\],

    "storage\_area\_ids": \[5, 6\],

    "storage\_location\_ids": \[10, 11, 12\],

    "product\_ids": \[3, 4\],

    "packaging\_ids": \[1\],

    "date\_from": "2024-01-01",

    "date\_to": "2025-01-01",

    "input\_type": "photo"  // "photo" | "manual" | "both"

},

"grouping": "by\_storage\_location", // "by\_warehouse" | "by\_storage\_area" | "
by\_storage\_location" | "by\_product" | "by\_packaging"

"metrics": \["total\_plants", "total\_price", "plants\_per\_square\_meter"\]

}

**Response:**

{

"report\_id": "rep-uuid-1",

"generated\_date": "2025-01-20T15:30:00",

"summary": {

    "total\_plants": 45000,

    "estimated\_total\_price": 920000.00,

    "warehouses\_included": 2,

    "storage\_locations\_included": 120

},

"data": \[

    {

      "group": "Storage Location 10",

      "total\_plants": 1200,

      "total\_price": 24600.00,

      "breakdown\_by\_product": \[...\]

    }

\]

}

#### GET `/api/analytics/report/{report_id}/export`

Export report to Excel or CSV.

**Query Parameters:**

- `format`: "excel" or "csv"

**Response:** Downloadable file

#### GET `/api/analytics/comparison`

Compare two storage locations, storage areas or warehouses.

**Query Parameters:**

- `type`: "storage\_location" | "storage\_area" | "warehouse"
- `id1`: ID of the first entity
- `id2`: ID of the second entity

#### GET `/api/analytics/empty-containers`

Detect storage locations with high proportion of empty containers.

#### POST `/api/analytics/ai-query` (PENDING)

Reserved endpoint for future generative AI queries.

**Note**: Leave this endpoint defined but without implementation. Will be for prompt system that
generates charts and reports on-the-fly.

### 6.6. User and Authentication Endpoints

#### POST `/api/auth/register`

Register new user.

#### POST `/api/auth/login`

Login.

**Response:**

{

"access\_token": "jwt-token",

"token\_type": "bearer",

"user": {

    "id": 1,

    "email": "user@example.com",

    "role": "admin"  // "admin" | "worker"

}

}

#### GET `/api/auth/me`

Get authenticated user information.

#### PUT `/api/users/{user_id}`

Update user information.

#### GET `/api/users`

List users (admin only).

### 6.7. Health Check Endpoint

#### GET `/api/health`

Verify API status.

**Response:**

{

"status": "healthy",

"database": "connected",

"celery": "running",

"version": "1.0.0"

}

---

## 7\. Async Processing with Celery

### 7.1. Use Cases

- **Multiple photos**: When more than 1 photo is uploaded simultaneously
- **Long processing**: Avoid HTTP timeouts (can take \~1 minute per photo on CPU)

### 7.2. Functionality

1. **Single photo**: Synchronous processing, immediate response
2. **Multiple photos**:
    - Create Celery tasks
    - Return task IDs
    - Frontend queries status periodically
    - Each task processes one complete photo (entire pipeline)

### 7.3. State Persistence

- States saved in Redis (Celery default): This updates the frontend
- **Additional**: Save states in PostgreSQL database for:
    - Traceability
    - Recovery after crashes
    - Historical queries

### 7.4. Internal Progress

Update progress of each task during execution:

\# Conceptual example

task.update\_state(

    state='PROCESSING',

    meta={'progress': 25, 'message': 'Segmenting image...'}

)

### 7.5. Failure Recovery

- Tasks should be idempotent when possible
- Configurable retries
- If server crashes, on restart it should be able to:
    - Resume pending tasks
    - Not reprocess completed tasks

### 7.6. Code Reuse

**CRITICAL**: The same services and repositories used in synchronous endpoints must be used in
Celery tasks. Do not create duplicate code for async processing.

---

## 8\. Pydantic Schemas

### 8.1. Purpose

- Input data validation
- Response serialization
- Automatic documentation in FastAPI

### 8.2. Structure

/schemas

warehouse\_schema.py

storage\_area\_schema.py

storage\_location\_schema.py

storage\_bin\_schema.py

photo\_processing\_session\_schema.py

stock\_movement\_schema.py

stock\_batch\_schema.py

configuration\_schema.py

user\_schema.py

analytics\_schema.py

### 8.3. Conventions

- All code in English
- Strong and explicit typing
- Custom validators when necessary

### 8.4. Transformation

Services are responsible for transforming:

Pydantic Schema (from controller) → SQLAlchemy Model (for repository)

SQLAlchemy Model (from repository) → Pydantic Schema (for controller)

---

## 9\. Centralized Configuration

### 9.1. Configuration Files

/config

config.yaml \# General configurations

.env \# Secrets (don't commit)

config\_loader.py \# Python class that reads configurations

### 9.2. config.yaml Structure

app:

name: "Cactus Counting System"

version: "1.0.0"

debug: true

database:

pool\_size: 10

max\_overflow: 20

ml:

sahi\_tile\_size: 512

detection\_confidence: 0.5

visualization\_colors:

    detections: "\#4CAF50"

    estimations: "\#FF9800"

celery:

broker\_url: "redis://redis:6379/0"

result\_backend: "redis://redis:6379/0"

### 9.3. Environment Variables (.env)

DATABASE\_URL=postgresql://user:pass@localhost:5432/dbname

SECRET\_KEY=supersecretkey

REDIS\_URL=redis://localhost:6379/0

### 9.4. Config Class

\# Conceptual example

class Config:

    def \_\_init\_\_(self):

        self.load\_yaml()

        self.load\_env()



    @property

    def database\_url(self):

        return os.getenv('DATABASE\_URL')

\# Specialized configurations

class DatabaseConfig(Config):

    \# Only DB configurations

class MLConfig(Config):

    \# Only ML configurations

**Principle**: Import only the necessary configuration in each module, don't import the entire
general config.

---

## 10\. Exception Handling

### 10.1. Centralized Exceptions

/exceptions

base\_exception.py

repository\_exceptions.py

service\_exceptions.py

ml\_exceptions.py

### 10.2. Structure

\# Conceptual example

class AppBaseException(Exception):

    def \_\_init\_\_(self, technical\_message: str, user\_message: str, code: int \= 500):

        self.technical\_message \= technical\_message

        self.user\_message \= user\_message

        self.code \= code

class StorageLocationNotFoundException(AppBaseException):

    def \_\_init\_\_(self, storage\_location\_id: int):

        super().\_\_init\_\_(

            technical\_message=f"Storage location with ID {storage\_location\_id} not found in DB",

            user\_message="The requested storage location does not exist",

            code=404

        )

### 10.3. Global Handler

FastAPI must have a global exception handler:

\# Conceptual example

@app.exception\_handler(AppBaseException)

async def app\_exception\_handler(request, exc: AppBaseException):

    return JSONResponse(

        status\_code=exc.code,

        content={

            "error": exc.user\_message,

            "detail": exc.technical\_message if DEBUG else None

        }

    )

### 10.4. Principles

- **Don't chain try-catch**: Avoid nested try-catch in multiple layers
- **Capture at the right level**:
    - Repositories: DB exceptions
    - Services: Business logic exceptions
    - Controllers: Rarely (global handler takes care)
- **User message vs. technical message**: Clearly separate
- **Automatic logging**: Each exception should be logged

---

## 11\. Logging System

### 11.1. Centralized Logger

/logging

logger\_config.py \# Main configuration

formatters.py \# Custom formatters

### 11.2. Logging Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General flow information
- **WARNING**: Unusual but manageable situations
- **ERROR**: Errors affecting functionality
- **CRITICAL**: Serious system failures

### 11.3. Logger per Class

Each class should have its own logger:

\# Conceptual example

class StorageLocationService:

    def \_\_init\_\_(self):

        self.logger \= logging.getLogger(self.\_\_class\_\_.\_\_name\_\_)



    def get\_storage\_location(self, storage\_location\_id: int):

        self.logger.info(f"Getting storage location {storage\_location\_id}")

        \# ...

        self.logger.debug(f"Storage location {storage\_location\_id} found with {result.plant\_quantity} plants")

### 11.4. Configuration

\# Conceptual example in logger\_config.py

logging.config.dictConfig({

    'version': 1,

    'formatters': {

        'detailed': {

            'format': '%(asctime)s \- %(name)s \- %(levelname)s \- %(message)s'

        }

    },

    'handlers': {

        'console': {

            'class': 'logging.StreamHandler',

            'formatter': 'detailed'

        },

        'file': {

            'class': 'logging.FileHandler',

            'filename': 'app.log',

            'formatter': 'detailed'

        }

    },

    'root': {

        'level': 'INFO',

        'handlers': \['console', 'file'\]

    }

})

### 11.5. Useful Logs, Not Excessive

- Log important flow points
- Log all exceptions
- Don't log every line of code
- Don't log sensitive information (passwords, tokens)

---

## 12\. Testing

### 12.1. Philosophy

Test-driven development (TDD when appropriate):

1. Write test
2. Implement functionality
3. Refactor
4. Commit

### 12.2. Types of Tests

#### Unit Tests

- Test each repository method individually
- Test each service method with repository mocks
- Test schema transformations

/tests

/unit

    /repositories

      test\_storage\_location\_repo.py

      test\_stock\_movement\_repo.py

    /services

      test\_storage\_location\_service.py

      test\_pipeline\_coordinator.py

    /schemas

      test\_transformations.py

#### Integration Tests

- Test complete flows endpoint → service → repository → DB
- Test complete pipeline with test photo
- Test Celery tasks

/tests

/integration

    test\_complete\_photo\_pipeline.py

    test\_stock\_movement\_flow.py

    test\_celery\_tasks.py

### 12.3. Test Photos

Include in project:

/tests

/fixtures

    /photos

      segment\_test\_1.jpg

      box\_test\_1.jpg

      multiple\_test.zip

### 12.4. Test Database

- Use separate database for tests
- Fixtures with test data
- Clean DB after each test

### 12.5. Coverage

- Goal: \>80% coverage
- Tool: pytest-cov
- Generate coverage reports in each phase

### 12.6. Execution

\# Unit tests

pytest tests/unit

\# Integration tests

pytest tests/integration

\# All tests with coverage

pytest \--cov=app \--cov-report=html

---

## 13\. Directory Structure

/project-cactus-counting

/app

    \_\_init\_\_.py

    main.py                 \# FastAPI initialization



    /config

      config.yaml

      config\_loader.py

      database\_config.py

      ml\_config.py



    /repositories

      \_\_init\_\_.py

      base\_repo.py

      /models

        \_\_init\_\_.py

        warehouse.py

        storage\_area.py

        storage\_location.py

        storage\_bin.py

        photo\_processing\_session.py

        stock\_movement.py

        stock\_batch.py

        \# ... all models



    /services

      \_\_init\_\_.py

      base\_service.py

      warehouse\_service.py

      storage\_area\_service.py

      storage\_location\_service.py

      \# ... other services



      /ml\_processing

        \_\_init\_\_.py

        pipeline\_coordinator.py

        localization\_service.py

        segmentation\_service.py

        detection\_service.py

        estimation\_service.py

        image\_processing\_service.py



    /controllers

      \_\_init\_\_.py

      location\_controller.py

      configuration\_controller.py

      stock\_controller.py

      analytics\_controller.py

      auth\_controller.py



    /schemas

      \_\_init\_\_.py

      warehouse\_schema.py

      storage\_area\_schema.py

      storage\_location\_schema.py

      \# ... other schemas



    /exceptions

      \_\_init\_\_.py

      base\_exception.py

      repository\_exceptions.py

      service\_exceptions.py

      ml\_exceptions.py



    /logging

      \_\_init\_\_.py

      logger\_config.py

      formatters.py



    /celery\_app

      \_\_init\_\_.py

      celery\_config.py

      tasks.py



    /utils

      \_\_init\_\_.py

      geolocation.py

      image\_utils.py

      date\_utils.py

/tests

    /unit

      /repositories

      /services

      /schemas

    /integration

    /fixtures

      /photos

/docs

    architecture.md

    api\_documentation.md

    ml\_pipeline.md

/planning

    phases.md                \# Development phases

    phase\_1\_repos.md         \# Phase 1 detail

    phase\_2\_services.md      \# Phase 2 detail

    \# ...

    current\_status.md        \# Current project status

    todo.md                  \# Pending tasks list

/scripts

    init\_db.py

    seed\_data.py

.env.example

.gitignore

Dockerfile

docker-compose.yml

requirements.txt

pytest.ini

README.md

---

## 14\. Code Conventions

### 14.1. Language

- **All code**: English (variables, functions, classes, comments, database entities, endpoints,
  schemas, logs)

### 14.2. Variable Names

\# CORRECT

def get\_storage\_location(storage\_location\_id: int) \-\> StorageLocationModel:

    query\_result \= self.session.query(StorageLocation).filter\_by(id=storage\_location\_id).first()

### 14.3. Strong Typing

\# CORRECT

def process\_photo(photo: UploadFile, metadata: PhotoMetadata) \-\> ProcessingResult:

    \# ...

\# INCORRECT

def process\_photo(photo, metadata):

    \# ...

### 14.4. Documentation

**DO NOT use docstrings in simple methods**:

\# INCORRECT \- unnecessary docstring

def get\_storage\_location(self, storage\_location\_id: int) \-\> StorageLocationModel:

    """

    Gets a storage location by its ID

    Args:

        storage\_location\_id: ID of the storage location

    Returns:

        Storage location model

    """

    return self.repo.get\_by\_id(storage\_location\_id)

\# CORRECT \- self-explanatory method

def get\_storage\_location(self, storage\_location\_id: int) \-\> StorageLocationModel:

    return self.repo.get\_by\_id(storage\_location\_id)

**Document only complex logic**:

\# CORRECT \- useful docstring

def estimate\_remaining\_plants(self, area\_pixels: int, pot\_size\_cm: float) \-\> int:

    """

    Estimates quantity of undetected plants based on area in pixels.



    Converts pixels to cm² using photo resolution and calculates

    how many pots of the specified size would fit in that area.

    """

    \# ...

### 14.5. Code Format

- **Tool**: Ruff
- **Lines**: Maximum 100 characters
- **Imports**: Organized (stdlib, third-party, local)
- **Run before commit**:

ruff check .

ruff format .

---

## 15\. Image Handling

### 15.1. Storage

/media

/original\_photos

    /{year}/{month}/{day}

      location\_{storage\_location\_id}\_{timestamp}.jpg

/visualized\_photos

    /{year}/{month}/{day}

      location\_{storage\_location\_id}\_{timestamp}\_viz.jpg

### 15.2. Compression

- Original photos: No additional compression (maintain quality)
- Visualized photos: Moderate compression (JPEG quality 85\)

### 15.3. Metadata

- Preserve original EXIF
- Add custom metadata: storage\_location\_id, timestamp, model\_version

### 15.4. Image Service

\# image\_service.py

class ImageService:

    def save\_original(self, photo: UploadFile, storage\_location\_id: int) \-\> str:

        \# Save original photo with metadata



    def create\_visualization(self, original\_photo\_path: str, detections: List, estimations: List) \-\> str:

        \# Create image with circles and masks



    def get\_image\_url(self, image\_path: str) \-\> str:

        \# Generate public URL

---

## 16\. Docker and Deployment

### 16.1. Dockerfile

\# Multi-stage build

FROM python:3.12-slim AS builder

WORKDIR /app

\# Install system dependencies needed for compilation

RUN apt-get update && apt-get install \-y \\

    build-essential \\

    libpq-dev \\

    && rm \-rf /var/lib/apt/lists/\*

\# Copy only requirements first (Docker cache)

COPY requirements.txt .

RUN pip install \--no-cache-dir \-r requirements.txt

\# Final stage

FROM python:3.12-slim

WORKDIR /app

\# Install runtime dependencies

RUN apt-get update && apt-get install \-y \\

    libpq5 \\

    && rm \-rf /var/lib/apt/lists/\*

\# Copy installed dependencies

COPY \--from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

\# Copy only necessary code

COPY app/ app/

COPY config/ config/

COPY scripts/ scripts/

\# Don't copy tests, docs, planning (use .dockerignore)

EXPOSE 8000

CMD \["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"\]

### 16.2. docker-compose.yml (Development)

version: '3.8'

services:

api:

    build: .

    ports:

      \- "8000:8000"

    volumes:

      \- ./app:/app/app

      \- ./media:/app/media

    environment:

      \- DATABASE\_URL=postgresql://user:pass@db:5432/cactus\_db

      \- REDIS\_URL=redis://redis:6379/0

    depends\_on:

      \- db

      \- redis

    command: uvicorn app.main:app \--host 0.0.0.0 \--port 8000 \--reload

celery\_worker:

    build: .

    volumes:

      \- ./app:/app/app

      \- ./media:/app/media

    environment:

      \- DATABASE\_URL=postgresql://user:pass@db:5432/cactus\_db

      \- REDIS\_URL=redis://redis:6379/0

    depends\_on:

      \- db

      \- redis

    command: celery \-A app.celery\_app.celery\_config worker \--loglevel=info

db:

    image: postgis/postgis:15-3.3

    environment:

      \- POSTGRES\_USER=user

      \- POSTGRES\_PASSWORD=pass

      \- POSTGRES\_DB=cactus\_db

    volumes:

      \- postgres\_data:/var/lib/postgresql/data

    ports:

      \- "5432:5432"

redis:

    image: redis:7-alpine

    ports:

      \- "6379:6379"

volumes:

postgres\_data:

### 16.3. .dockerignore

tests/

docs/

planning/

.git/

.env

\_\_pycache\_\_/

\*.pyc

.pytest\_cache/

.coverage

htmlcov/

---

## 17\. Development Plan by Phases

### Phase 0: Initial Setup

- [ ] Configure Git repository
- [ ] Create directory structure
- [ ] Setup virtual environment
- [ ] Install base dependencies
- [ ] Configure Ruff and pre-commit hooks
- [ ] Create .env.example
- [ ] Document in `/planning/phase_0_setup.md`

### Phase 1: Repositories and Models

- [ ] Create SQLAlchemy models for all tables
- [ ] Implement BaseRepository
- [ ] Implement specific repositories: \- \[ \] WarehouseRepo \- \[ \] StorageAreaRepo \- \[ \]
  StorageLocationRepo \- \[ \] StorageBinRepo \- \[ \] StorageBinTypeRepo \- \[ \]
  PhotoProcessingSessionRepo \- \[ \] StockMovementRepo \- \[ \] StockBatchRepo \- \[ \]
  ProductRepo \- \[ \] ProductCategoryRepo \- \[ \] ProductFamilyRepo \- \[ \]
  PackagingCatalogRepo \- \[ \] PackagingTypeRepo \- \[ \] PackagingMaterialRepo \- \[ \]
  PackagingColorRepo \- \[ \] StorageLocationConfigRepo \- \[ \] DensityParametersRepo \- \[ \]
  UserRepo \- \[ \] DetectionRepo \- \[ \] EstimationRepo \- \[ \] ProductStateRepo \- \[ \]
  ProductSizeRepo
- [ ] Unit tests for each repository
- [ ] Document in `/planning/phase_1_repos.md`
- [ ] Commit: "feat: implement all repositories and models"

### Phase 2: Base Services

- [ ] Create BaseService
- [ ] Implement services for simple entities: \- \[ \] ProductService \- \[ \]
  PackagingCatalogService \- \[ \] WarehouseService \- \[ \] StorageAreaService \- \[ \]
  StorageLocationService
- [ ] Unit tests with mocks
- [ ] Document in `/planning/phase_2_base_services.md`
- [ ] Commit: "feat: implement base services"

### Phase 3: Complex Services

- [ ] Implement business logic services: \- \[ \] PhotoProcessingSessionService \- \[ \]
  StockMovementService \- \[ \] StockBatchService \- \[ \] StorageLocationConfigService
- [ ] Unit tests
- [ ] Document in `/planning/phase_3_complex_services.md`
- [ ] Commit: "feat: implement complex business services"

### Phase 4: Machine Learning Pipeline

- [ ] Implement LocalizationService
- [ ] Implement SegmentationService
- [ ] Implement DetectionService (with SAHI)
- [ ] Implement EstimationService
- [ ] Implement ImageProcessingService (visualizations)
- [ ] Implement PipelineCoordinator
- [ ] Integration tests with test photos
- [ ] Document in `/planning/phase_4_ml_pipeline.md`
- [ ] Commit: "feat: implement complete ML pipeline"

### Phase 5: Pydantic Schemas

- [ ] Create all request/response schemas
- [ ] Custom validators
- [ ] Schema ↔ model transformation tests
- [ ] Document in `/planning/phase_5_schemas.md`
- [ ] Commit: "feat: implement pydantic schemas"

### Phase 6: Controllers \- Location

- [ ] Implement location endpoints
- [ ] Integration tests
- [ ] Document in `/planning/phase_6_location_controllers.md`
- [ ] Commit: "feat: implement location controllers"

### Phase 7: Controllers \- Configuration

- [ ] Implement configuration endpoints
- [ ] Integration tests
- [ ] Document in `/planning/phase_7_configuration_controllers.md`
- [ ] Commit: "feat: implement configuration controllers"

### Phase 8: Controllers \- Stock and Celery

- [ ] Implement stock input endpoints
- [ ] Configure Celery
- [ ] Implement async tasks
- [ ] Integration tests with Celery
- [ ] Document in `/planning/phase_8_stock_celery.md`
- [ ] Commit: "feat: implement stock controllers and celery tasks"

### Phase 9: Controllers \- Analytics

- [ ] Implement analytics endpoints
- [ ] Excel/CSV export
- [ ] Integration tests
- [ ] Document in `/planning/phase_9_analytics.md`
- [ ] Commit: "feat: implement analytics controllers"

### Phase 10: Authentication and Users

- [ ] Implement JWT authentication
- [ ] Auth and user endpoints
- [ ] Authorization middleware
- [ ] Tests
- [ ] Document in `/planning/phase_10_auth.md`
- [ ] Commit: "feat: implement authentication and users"

### Phase 11: Exceptions and Logging

- [ ] Implement exception system
- [ ] Configure centralized logging
- [ ] Global exception handlers
- [ ] Document in `/planning/phase_11_exceptions_logging.md`
- [ ] Commit: "feat: implement exceptions and logging"

### Phase 12: Centralized Configuration

- [ ] Create configuration system
- [ ] Migrate hardcoded values to config
- [ ] Document in `/planning/phase_12_config.md`
- [ ] Commit: "feat: implement centralized configuration"

### Phase 13: Docker and Deployment

- [ ] Create optimized Dockerfile
- [ ] Create docker-compose.yml
- [ ] DB initialization scripts
- [ ] Document in `/planning/phase_13_docker.md`
- [ ] Commit: "feat: add docker configuration"

### Phase 14: Final Documentation

- [ ] Complete README.md
- [ ] API documentation (automatic with FastAPI)
- [ ] Contribution guide
- [ ] Document in `/docs/`
- [ ] Commit: "docs: complete project documentation"

### Phase 15: Optimization and Refactoring

- [ ] Review test coverage
- [ ] Optimize slow queries
- [ ] Refactor duplicate code
- [ ] Document in `/planning/phase_15_optimization.md`
- [ ] Commit: "refactor: optimize and clean code"

---

## 18\. Project Management

### 18.1. Documents in /planning

#### phases.md

List of all phases with general progress checkboxes.

#### phase\_X\_name.md

Detail of each phase:

- Objectives
- Specific tasks
- Acceptance criteria
- Technical notes
- Problems encountered

#### current\_status.md

Updated by each programmer at the end of their session:

\# Current Project Status

\*\*Date\*\*: 2025-01-20

\*\*Programmer\*\*: John Doe

\*\*Current Phase\*\*: Phase 4 \- ML Pipeline

\#\# What I did today

\- Implemented SegmentationService

\- Added tests for segmentation

\- Problems with mask size (resolved)

\#\# Next step

\- Continue with DetectionService

\- Implement SAHI

\#\# Blockers

\- None

\#\# Notes

\- Changed mask format from numpy array to PIL Image for better performance

#### todo.md

Current phase task list with priorities.

### 18.2. Commits

Follow commit convention:

feat: new functionality

fix: bug fix

refactor: refactoring without functionality change

test: add or modify tests

docs: documentation changes

chore: maintenance tasks

### 18.3. Branching

main

└── develop

       ├── feature/phase-1-repositories

       ├── feature/phase-2-services

       └── feature/phase-4-ml-pipeline

Merge to develop upon completing each phase with all tests passing.

---

## 19\. Libraries and Dependencies

### 19.1. requirements.txt

\# Web Framework

fastapi==0.109.0

uvicorn\[standard\]==0.27.0

pydantic==2.5.3

pydantic-settings==2.1.0

\# Database

sqlalchemy==2.0.25

psycopg2-binary==2.9.9

alembic==1.13.1

\# Async Tasks

celery==5.3.6

redis==5.0.1

\# Machine Learning

ultralytics==8.1.20

opencv-python-headless==4.9.0.80

numpy==1.26.3

pillow==10.2.0
[Turn on screen reader support](https://docs.google.com/document/d/1SF9Bx50syPbm_VcH_Wt0sYwgebb4jyGDb6tYdYtlsWo/edit?tab=t.0#)
To enable screen reader support, press Ctrl+Alt+Z To learn about keyboard shortcuts, press
Ctrl+slash
Banner hidden
Show side panel

torch==2.1.2

torchvision==0.16.2

\# Image Processing

scikit-image==0.22.0

\# Geolocation

shapely==2.0.2

\# Authentication

python-jose\[cryptography\]==3.3.0

passlib\[bcrypt\]==1.7.4

python-multipart==0.0.6

\# Excel/CSV

openpyxl==3.1.2

pandas==2.2.0

\# Testing

pytest==8.0.0

pytest-asyncio==0.23.4

pytest-cov==4.1.0

pytest-mock==3.12.0

httpx==0.26.0

\# Code Quality

ruff==0.1.14

\# Utilities

python-dateutil==2.8.2

pyyaml==6.0.1

---

## 20\. Final Notes and Best Practices

### 20.1. SOLID Principles

- **Single Responsibility**: Each class has a clear responsibility
- **Open/Closed**: Extend without modifying (use inheritance and composition)
- **Liskov Substitution**: Subclasses must be interchangeable
- **Interface Segregation**: Specific interfaces, not huge generic ones
- **Dependency Inversion**: Depend on abstractions, not concrete implementations

### 20.2. DRY (Don't Repeat Yourself)

- Reuse code between repositories
- Reuse code between services
- Same pipeline for Celery and synchronous endpoints
- Same error handling throughout the app

### 20.3. KISS (Keep It Simple, Stupid)

- Short and clear methods
- Don't over-engineer
- If a method does an obvious thing, it doesn't need a docstring

### 20.4. YAGNI (You Aren't Gonna Need It)

- Don't implement functionality "just in case"
- Implement only what's specified in this plan
- The generative AI endpoint is marked as PENDING, don't implement yet

### 20.5. Performance

- **Queries**: Use eager loading when necessary, lazy when not
- **Images**: Process in chunks, don't load everything in memory
- **Celery**: For long operations, don't block main thread
- **Caching**: Consider caching configurations that don't change frequently

### 20.6. Security

- **Don't commit secrets**: Use .env
- **Validate inputs**: Pydantic validates automatically
- **SQL Injection**: SQLAlchemy protects automatically
- **Authentication**: JWT with expiration
- **CORS**: Configure correctly in production

### 20.7. Monitoring

- Structured logs to facilitate search
- Performance metrics (photo processing time)
- Alerts when Celery tasks fail repeatedly

---

## 21\. Pre-Production Checklist

Before considering the system ready for production:

- [ ] All tests pass (unit and integration)
- [ ] Test coverage \>80%
- [ ] Complete documentation in `/docs`
- [ ] README.md updated with installation instructions
- [ ] Environment variables documented in .env.example
- [ ] Dockerfile and docker-compose.yml functional
- [ ] Logging system configured
- [ ] Robust exception system
- [ ] Acceptable performance (photo processing benchmark)
- [ ] Basic security review completed
- [ ] Backup strategy defined for database
- [ ] Rollback plan in case of failure
- [ ] Basic monitoring configured

---

## 22\. Resources and References

### 22.1. Official Documentation

- FastAPI: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- SQLAlchemy: [https://docs.sqlalchemy.org](https://docs.sqlalchemy.org)
- Pydantic: [https://docs.pydantic.dev](https://docs.pydantic.dev)
- Celery: [https://docs.celeryq.dev](https://docs.celeryq.dev)
- Ultralytics YOLO: [https://docs.ultralytics.com](https://docs.ultralytics.com)
- PostgreSQL: [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)

### 22.2. Development Tools

- Ruff: [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)
- Pytest: [https://docs.pytest.org](https://docs.pytest.org)
- Docker: [https://docs.docker.com](https://docs.docker.com)

### 22.3. Additional Resources

- Use Context7 MCP for updated library documentation
- Search the internet when necessary
- Consult this engineering document frequently

---

## Conclusion

This engineering document is the complete guide for the development of the Automated Cactus and
Succulent Counting System. It covers from database architecture to deployment with Docker, including
all necessary technical aspects.

**Key principles to remember**:

1. Everything is connected: services use services, repos use repos
2. The ML pipeline is an integral part of the API, not something separate
3. All code in English
4. Tests before considering something finished
5. Document progress in `/planning`
6. Frequent and descriptive commits
7. Strong typing throughout the code
8. Centralized configuration
9. Well-handled exceptions and logs
10. Simplicity over complexity

Any developer who reads this document should be able to understand the complete system and continue
development following the established phases.
