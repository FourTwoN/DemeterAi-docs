# [C024] Create Price List - POST /api/price-list

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [SCH007]
    - Blocked by: [SVC011-price-list-service, DB027-price-list-model]

## Description

Create price list entry for product + packaging + size combination.

## Acceptance Criteria

- [ ] **AC1**: Request body: product_id, packaging_id, product_size_id, price, currency
- [ ] **AC2**: Validate unique constraint (one price per combination)
- [ ] **AC3**: Return HTTP 201

```python
@router.post("/price-list", response_model=PriceListResponse, status_code=201)
async def create_price_list(
    request: PriceListRequest,
    service: PriceListService = Depends()
):
    """Create price list entry."""
    return await service.create_price(request)
```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
