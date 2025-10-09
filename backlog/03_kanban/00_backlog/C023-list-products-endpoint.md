# [C023] List Products - GET /api/products

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [SCH016]
  - Blocked by: [SVC010-product-service, DB017-products-model]

## Description

List all products with optional filtering by category, family, state.

## Acceptance Criteria

- [ ] **AC1**: Query params: product_category_id, product_family_id, product_state
- [ ] **AC2**: Pagination (skip, limit)
- [ ] **AC3**: Return product details with family and category

```python
@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    product_category_id: Optional[int] = None,
    product_family_id: Optional[int] = None,
    product_state: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    service: ProductService = Depends()
):
    """List products with filters."""
    return await service.list_products(
        product_category_id, product_family_id, product_state, skip, limit
    )
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
