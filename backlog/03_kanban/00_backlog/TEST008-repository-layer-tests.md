# [TEST008] Repository Layer Tests

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-02
- **Priority**: `high`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [TEST001]

## Description

Test repository layer with real database: CRUD operations, complex queries, transactions, eager
loading.

## Acceptance Criteria

- [ ] Test all CRUD methods (create, get, update, delete)
- [ ] Test filtering and searching
- [ ] Test pagination
- [ ] Test relationships (joinedload, selectinload)
- [ ] Test transactions (commit, rollback)
- [ ] Coverage >85% for repositories

## Implementation

```python
@pytest.mark.asyncio
async def test_warehouse_repository_crud(db_session):
    repo = WarehouseRepository(Warehouse, db_session)

    # Create
    warehouse = await repo.create({
        "name": "Test Warehouse",
        "code": "TW001",
        "geom": "POLYGON(...)"
    })
    assert warehouse.id is not None

    # Read
    fetched = await repo.get(warehouse.id)
    assert fetched.name == "Test Warehouse"

    # Update
    updated = await repo.update(warehouse.id, {"name": "Updated Warehouse"})
    assert updated.name == "Updated Warehouse"

    # Delete
    deleted = await repo.delete(warehouse.id)
    assert deleted is True

@pytest.mark.asyncio
async def test_repository_eager_loading(db_session):
    """Test N+1 query prevention."""
    repo = PhotoSessionRepository(PhotoSession, db_session)

    # Without eager loading (N+1 queries)
    sessions = await repo.get_multi()
    for session in sessions:
        _ = session.storage_location  # Triggers separate query

    # With eager loading (1 query)
    sessions = await repo.get_multi_with_location()
    for session in sessions:
        _ = session.storage_location  # No additional query
```

## Testing

- Test with real PostgreSQL database
- Verify queries optimized (no N+1)
- Test transaction isolation
- Check query performance

---
**Card Created**: 2025-10-09
