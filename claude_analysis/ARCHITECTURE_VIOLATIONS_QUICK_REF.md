# Architecture Violations - Quick Reference

## Sprint 04 Controllers - Critical Issues

**Date**: 2025-10-21
**Impact**: 5 controllers, 25+ endpoints, ENTIRE API LAYER

---

## Violations Summary

| Controller              | Repo Imports  | Endpoints | Complexity    | Risk         |
|-------------------------|---------------|-----------|---------------|--------------|
| config_controller.py    | 2             | 3         | LOW           | LOW          |
| analytics_controller.py | 1             | 3         | LOW           | LOW          |
| product_controller.py   | 3             | 6         | MEDIUM        | MEDIUM       |
| stock_controller.py     | 2 + nested    | 7         | HIGH          | HIGH         |
| location_controller.py  | 4             | 6         | VERY HIGH     | VERY HIGH    |
| **TOTAL**               | **12+ repos** | **25**    | **13 points** | **CRITICAL** |

---

## The Problem

**Controllers import Repositories directly**:

```python
# ❌ WRONG (current state)
from app.repositories.product_repository import ProductRepository

def get_product_service(session):
    product_repo = ProductRepository(session)  # ❌ Controller knows about repos
    return ProductService(product_repo)
```

**Clean Architecture violation**: Controller → Repository (skipping Service layer)

---

## The Solution

**ServiceFactory for dependency injection**:

```python
# ✅ CORRECT (after refactor)
from app.factories.service_factory import ServiceFactory

def get_factory(session):
    return ServiceFactory(session)

@router.get("/products")
async def list_products(factory: ServiceFactory = Depends(get_factory)):
    service = factory.get_product_service()  # ✅ No repo knowledge
    return await service.get_all()
```

**Clean Architecture**: Controller → Factory → Service → Repository

---

## Files Affected

### NEW FILE (1)

- `app/factories/service_factory.py` (~500 lines)
    - Centralized dependency injection
    - 35 service getter methods
    - Lazy loading with caching

### MODIFIED FILES (5)

1. `app/controllers/config_controller.py` (~30 lines)
2. `app/controllers/analytics_controller.py` (~25 lines)
3. `app/controllers/product_controller.py` (~60 lines)
4. `app/controllers/stock_controller.py` (~90 lines)
5. `app/controllers/location_controller.py` (~100 lines)

**Total**: ~305 lines changed, ~150 lines deleted (duplication)

---

## Implementation Order

1. Create ServiceFactory (3h) - BLOCKING
2. Refactor config_controller.py (30min) - EASY
3. Refactor analytics_controller.py (30min) - EASY
4. Refactor product_controller.py (1h) - MEDIUM
5. Refactor stock_controller.py (1.5h) - HARD
6. Refactor location_controller.py (2h) - VERY HARD
7. Integration testing (1h)

**Total**: ~9.5 hours

---

## Quality Gates

- [ ] ServiceFactory created and tested
- [ ] All repository imports removed from controllers
- [ ] All endpoints use factory pattern
- [ ] All controller tests pass
- [ ] No behavior changes (same API responses)
- [ ] Type hints correct (mypy passes)

---

## Detailed Plan

See: `/home/lucasg/proyectos/DemeterDocs/ARCHITECTURE_REMEDIATION_PLAN.md`

---

## Next Action

**FOR PYTHON EXPERT**: Start Phase 1 - Create ServiceFactory

**Command**:

```bash
# Create factory directory
mkdir -p /home/lucasg/proyectos/DemeterDocs/app/factories

# Start implementation
vim /home/lucasg/proyectos/DemeterDocs/app/factories/service_factory.py
```

**Template**: See detailed plan for ServiceFactory design pattern

---

**Team Leader Status**: PLAN COMPLETE - Ready for delegation
