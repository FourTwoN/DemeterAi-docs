# Epic 017: Documentation & Developer Guides

**Status**: Ready
**Sprint**: Sprint-05 (Week 11-12) - continuous
**Priority**: medium (developer experience)
**Total Story Points**: 30
**Total Cards**: 6

---

## Goal

Create comprehensive developer documentation including API documentation, architecture guides, onboarding tutorials, and troubleshooting guides for team productivity.

---

## Success Criteria

- [ ] OpenAPI documentation auto-generated and complete
- [ ] Architecture decision records (ADRs) documented
- [ ] Developer onboarding guide (<2 hours to productive)
- [ ] Troubleshooting guide for common issues
- [ ] Code examples for all major workflows
- [ ] Deployment runbook documented

---

## Cards List (6 cards, 30 points)

### API Documentation (10 points)
- **DOC001**: OpenAPI spec generation (FastAPI auto-docs) (3pts)
- **DOC002**: API endpoint documentation (descriptions, examples) (5pts)
- **DOC003**: Postman collection export (2pts)

### Architecture Documentation (10 points)
- **DOC004**: Architecture decision records (ADRs) (5pts)
- **DOC005**: System architecture diagrams (3pts)
- **DOC006**: Database schema documentation (2pts)

### Developer Guides (10 points)
- **DOC007**: Developer onboarding guide (5pts)
- **DOC008**: Local development setup (2pts)
- **DOC009**: Troubleshooting guide (3pts)

---

## Dependencies

**Blocked By**: All feature implementations
**Blocks**: Team productivity, onboarding speed

---

## Technical Approach

**OpenAPI Auto-Generation**:
```python
from fastapi import FastAPI

app = FastAPI(
    title="DemeterAI v2.0 API",
    description="ML-powered plant inventory management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.post(
    "/api/stock/manual",
    summary="Manual stock initialization",
    description="Initialize stock count manually without photo/ML processing. Requires product to match location config.",
    response_model=StockMovementResponse,
    status_code=201,
    tags=["Stock Management"]
)
async def manual_init(request: ManualStockInitRequest):
    """
    Create manual stock initialization.

    Args:
        request: Manual initialization request with location, product, quantity

    Returns:
        Stock movement with batch_code

    Raises:
        ProductMismatchException: Product doesn't match config
        ConfigNotFoundException: Location has no config
    """
    pass
```

**ADR Template**:
```markdown
# ADR-002: UUID for s3_images.image_id

## Status
Accepted

## Context
Need unique identifier for S3 images before database insertion.

## Decision
Use UUID generated in API (not database SERIAL).

## Consequences
+ Idempotent uploads
+ S3 key pre-generation
+ No race conditions
- 16 bytes vs 8 bytes overhead
```

---

**Epic Owner**: Tech Lead
**Created**: 2025-10-09
