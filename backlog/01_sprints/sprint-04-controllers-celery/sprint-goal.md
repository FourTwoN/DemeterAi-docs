# Sprint 04: API Controllers + Celery Integration
## Sprint Goal

**Duration**: Week 9-10 (Days 41-50)
**Team Capacity**: 80 story points
**Committed**: 78 story points

---

## Goal Statement

> **"Expose complete REST API with Celery async processing, enabling end-to-end photo upload → ML processing → results retrieval workflow."**

---

## Success Criteria

- [ ] All API endpoints implemented (stock, location, config, analytics, auth)
- [ ] Celery app configured (GPU/CPU/IO workers)
- [ ] Celery chord pattern working (ML parent → children → callback)
- [ ] POST /api/stock/photo triggers ML pipeline asynchronously
- [ ] GET /api/stock/tasks/{task_id} returns processing status
- [ ] Pydantic schemas for all requests/responses
- [ ] Authentication working (JWT, 15min expiration)
- [ ] OpenAPI docs complete at `/docs`
- [ ] Integration tests pass (FastAPI TestClient + Celery)

---

## Sprint Scope

### In Scope (34 cards, 78 points)

**Celery Infrastructure (CEL001-CEL008)**: 20 points
- CEL001: Celery app configuration (broker, backend, routing)
- CEL002: GPU worker setup (pool=solo, CUDA_VISIBLE_DEVICES)
- CEL003: CPU worker setup (pool=prefork)
- CEL004: IO worker setup (pool=gevent)
- CEL005: ML parent task (segments → spawns children)
- CEL006: ML child tasks (SAHI detection, direct detection, estimation)
- CEL007: Callback task (aggregate results, create batches)
- CEL008: Circuit breaker for S3 uploads

**API Controllers (C001-C026)**: 38 points
- Stock controllers (photo upload, manual init, movement tracking)
- Location controllers (GET warehouses, areas, locations)
- Configuration controllers (POST/GET config, products, packaging)
- Analytics controllers (reports, comparisons, exports)
- Auth controllers (login, token refresh, user management)

**Pydantic Schemas (SCH001-SCH020)**: 20 points
- Request/response schemas for all endpoints
- Validation rules, nested schemas

### Out of Scope
- ❌ Deployment (Sprint 05)
- ❌ Observability (Sprint 05)

---

## Key Deliverables

1. `app/controllers/` - 26 FastAPI controllers
2. `app/schemas/` - 20 Pydantic schema files
3. `app/celery_app.py` - Celery configuration
4. `app/tasks/ml_tasks.py` - ML parent/child/callback tasks
5. Integration tests (httpx TestClient + Celery Eager mode)

---

## Dependencies

**Blocked By**: Sprint 03 (Services), Sprint 02 (ML pipeline)
**Blocks**: Sprint 05 (Deployment needs working API)

---

**Sprint Owner**: API Lead
**Last Updated**: 2025-10-09
