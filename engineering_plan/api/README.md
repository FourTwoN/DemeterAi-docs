# API Documentation

**Version:** 1.0
**Last Updated:** 2025-10-08

---

## Overview

DemeterAI exposes a **RESTful API** built with FastAPI 0.118.0. All endpoints follow REST
conventions and return JSON responses.

**Base URL:** `http://localhost:8000/api` (development)

**OpenAPI Docs:** `http://localhost:8000/docs` (interactive Swagger UI)

---

## Endpoint Categories

| Category          | Purpose                              | Key Endpoints                                   |
|-------------------|--------------------------------------|-------------------------------------------------|
| **Stock**         | Photo upload, manual init, movements | POST /stock/photo, POST /stock/manual           |
| **Locations**     | Warehouse, area, location CRUD       | GET /locations/warehouses, GET /locations/{id}  |
| **Analytics**     | Reports, exports, comparisons        | POST /analytics/report, GET /analytics/export   |
| **Configuration** | Storage location config              | POST /config/storage-location, GET /config/{id} |
| **Auth**          | JWT login, user management           | POST /auth/login, GET /auth/me                  |

---

## Stock Endpoints

### POST /api/stock/photo

**Purpose:** Upload photo for ML processing (primary initialization method)

**Request:**

```http
POST /api/stock/photo
Content-Type: multipart/form-data

file: (binary)
user_id: 123
```

**Response (HTTP 202 Accepted):**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Photo uploaded successfully. Check /api/stock/tasks/status?task_id=..."
}
```

**See:
** [../../flows/procesamiento_ml_upload_s3_principal/](../../flows/procesamiento_ml_upload_s3_principal/README.md)

---

### POST /api/stock/manual

**Purpose:** Manual stock initialization (no photo/ML)

**Request:**

```json
{
  "storage_location_id": 123,
  "product_id": 45,
  "packaging_catalog_id": 12,
  "product_size_id": 3,
  "quantity": 1500,
  "planting_date": "2025-09-15",
  "notes": "Initial count from Excel"
}
```

**Response (HTTP 201 Created):**

```json
{
  "stock_movement_id": "550e8400-e29b-41d4-a716-446655440000",
  "stock_batch_id": 5432,
  "batch_code": "LOC123-PROD45-20251008-001",
  "quantity": 1500,
  "created_at": "2025-10-08T14:30:00Z",
  "message": "Manual initialization completed"
}
```

**Errors:**

- `400` - Product/packaging mismatch with config
- `404` - Location not found
- `422` - Validation error (quantity ≤ 0)

**See:
** [../../engineering_plan/workflows/manual_initialization.md](../../engineering_plan/workflows/manual_initialization.md)

---

### GET /api/stock/tasks/status

**Purpose:** Poll task status (for async photo processing)

**Query Parameters:**

- `task_id` (required): Celery task UUID

**Response (HTTP 200 OK):**

```json
{
  "task_id": "550e8400-...",
  "status": "completed",
  "result": {
    "session_id": 789,
    "total_detected": 1234,
    "total_estimated": 567,
    "batch_ids": [5432, 5433],
    "processed_image_url": "https://s3.../processed/2025/10/08/uuid_viz.avif"
  }
}
```

**Statuses:** `pending`, `processing`, `completed`, `failed`

---

## Location Endpoints

### GET /api/locations/warehouses

**Purpose:** List all warehouses

**Response (HTTP 200 OK):**

```json
{
  "warehouses": [
    {
      "id": 1,
      "code": "WH-01",
      "name": "Greenhouse North",
      "type": "greenhouse",
      "area_m2": 5000.0,
      "centroid": {"lat": -33.4489, "lon": -70.6483}
    }
  ]
}
```

---

### GET /api/locations/{id}

**Purpose:** Get location details (warehouse, area, or storage_location)

**Response (HTTP 200 OK):**

```json
{
  "id": 123,
  "code": "LOC-123",
  "name": "Column 5, Row 3",
  "storage_area_id": 10,
  "area_m2": 12.5,
  "configuration": {
    "product_id": 45,
    "product_name": "Echeveria Golden",
    "packaging_id": 12,
    "packaging_name": "R7 pot"
  },
  "current_stock": {
    "total_plants": 1500,
    "batches": 3
  }
}
```

---

## Analytics Endpoints

### POST /api/analytics/report

**Purpose:** Generate custom report with filters

**Request:**

```json
{
  "warehouse_ids": [1, 2],
  "product_ids": [45, 50],
  "date_from": "2025-09-01",
  "date_to": "2025-09-30",
  "group_by": ["warehouse", "product"],
  "include_movements": true
}
```

**Response (HTTP 200 OK):**

```json
{
  "report_data": [
    {
      "warehouse_id": 1,
      "warehouse_name": "Greenhouse North",
      "product_id": 45,
      "product_name": "Echeveria Golden",
      "total_plants": 5000,
      "movements": {
        "plantado": 500,
        "muerte": -200,
        "ventas": -300
      }
    }
  ],
  "totals": {
    "total_plants": 5000,
    "total_movements": 0
  }
}
```

---

## Authentication

### POST /api/auth/login

**Purpose:** Obtain JWT access token

**Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response (HTTP 200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Token Expiration:**

- Access token: 15 minutes
- Refresh token: 7 days

---

### GET /api/auth/me

**Purpose:** Get current authenticated user

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response (HTTP 200 OK):**

```json
{
  "id": 123,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "admin"
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": "Product mismatch",
  "detail": "The product you entered (Sedum Blue) does not match the configured product (Echeveria Golden)",
  "code": "PRODUCT_MISMATCH",
  "timestamp": "2025-10-08T14:30:00Z"
}
```

### HTTP Status Codes

| Code    | Meaning               | Example                            |
|---------|-----------------------|------------------------------------|
| **200** | OK                    | GET requests successful            |
| **201** | Created               | POST /stock/manual successful      |
| **202** | Accepted              | Async task started (photo upload)  |
| **400** | Bad Request           | Product mismatch, validation error |
| **401** | Unauthorized          | Missing/invalid JWT token          |
| **403** | Forbidden             | Insufficient permissions           |
| **404** | Not Found             | Resource doesn't exist             |
| **422** | Unprocessable Entity  | Pydantic validation error          |
| **500** | Internal Server Error | Unexpected error                   |

---

## Rate Limiting (Future)

**Current:** No rate limiting

**Planned:**

- 100 requests/minute per IP (general endpoints)
- 10 requests/minute for /stock/photo (resource-intensive)

---

## Next Steps

- **Detailed Endpoint Specs:** See individual files in this directory
- **Workflows:** See [../workflows/README.md](../workflows/README.md)
- **Backend Implementation:** See [../backend/controller_layer.md](../backend/controller_layer.md)

---

**Document Owner:** DemeterAI Engineering Team
**API Version:** v1
**Last Reviewed:** 2025-10-08
