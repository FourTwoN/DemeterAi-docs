# [TEST009] Service Layer Tests

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-03
- **Priority**: `high`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [TEST001, TEST010]

## Description

Test service layer with mocked repositories: business logic validation, orchestration, error
handling.

## Acceptance Criteria

- [ ] Test business logic isolated from database
- [ ] Mock repositories (pytest-mock)
- [ ] Test service orchestration (calls multiple services)
- [ ] Test error handling and exceptions
- [ ] Test validation rules
- [ ] Coverage >80% for services

## Implementation

```python
@pytest.fixture
def mock_stock_repo(mocker):
    repo = mocker.Mock(spec=StockMovementRepository)
    repo.create.return_value = StockMovement(
        id=1,
        movement_type="manual_init",
        quantity=100
    )
    return repo

@pytest.fixture
def stock_service(mock_stock_repo):
    return StockMovementService(
        repo=mock_stock_repo,
        config_service=mocker.Mock(),
        batch_service=mocker.Mock()
    )

@pytest.mark.asyncio
async def test_manual_stock_init_validation(stock_service):
    """Test business validation in service layer."""
    # Mock config check
    stock_service.config_service.get_by_location.return_value = None

    with pytest.raises(ConfigNotFoundException):
        await stock_service.create_manual_initialization(
            ManualStockInitRequest(
                location_id=1,
                product_id=10,
                quantity=100
            )
        )

@pytest.mark.asyncio
async def test_service_orchestration(stock_service):
    """Test service calls other services correctly."""
    await stock_service.create_manual_initialization(request)

    # Verify service calls
    stock_service.config_service.get_by_location.assert_called_once_with(1)
    stock_service.batch_service.create_from_movement.assert_called_once()
```

## Testing

- Test services in isolation (mocked repos)
- Test business logic without DB
- Test error handling
- Verify service orchestration

---
**Card Created**: 2025-10-09
