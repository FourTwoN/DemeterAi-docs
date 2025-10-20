"""Unit tests for StockBatchService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock StockBatchRepository
- Test CRUD operations (create, get_by_id, update_quantity)
- Test batch code uniqueness validation
- Test error handling

Coverage target: ≥80%

Test categories:
- create_stock_batch: success, duplicate code
- get_batch_by_id: success, not found
- update_batch_quantity: success

See:
    - Service: app/services/stock_batch_service.py
    - Schema: app/schemas/stock_batch_schema.py
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.stock_batch_schema import (
    StockBatchCreateRequest,
    StockBatchResponse,
)
from app.services.stock_batch_service import StockBatchService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_batch_repo():
    """Create mock StockBatchRepository."""
    return AsyncMock()


@pytest.fixture
def batch_service(mock_batch_repo):
    """Create StockBatchService with mocked dependencies."""
    return StockBatchService(batch_repo=mock_batch_repo)


@pytest.fixture
def mock_batch():
    """Create mock StockBatch model instance."""
    batch = Mock()
    batch.batch_id = 1
    batch.batch_code = "BATCH-001"
    batch.current_storage_bin_id = 10
    batch.product_id = 5
    batch.product_state_id = 2
    batch.product_size_id = 3
    batch.has_packaging = True
    batch.packaging_catalog_id = 7
    batch.quantity_initial = 100
    batch.quantity_current = 100
    batch.quantity_empty_containers = 0
    batch.quality_score = Decimal("4.5")
    batch.planting_date = date(2025, 9, 15)
    batch.created_at = datetime(2025, 10, 20, 14, 30, 0)
    batch.updated_at = None
    batch.custom_attributes = {"origin": "greenhouse_A"}
    return batch


@pytest.fixture
def create_request():
    """Create sample StockBatchCreateRequest."""
    return StockBatchCreateRequest(
        batch_code="BATCH-001",
        current_storage_bin_id=10,
        product_id=5,
        product_state_id=2,
        product_size_id=3,
        has_packaging=True,
        packaging_catalog_id=7,
        quantity_initial=100,
        quantity_current=100,
        quantity_empty_containers=0,
        quality_score=Decimal("4.5"),
        planting_date=date(2025, 9, 15),
        custom_attributes={"origin": "greenhouse_A"},
    )


# ============================================================================
# create_stock_batch tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_stock_batch_success(batch_service, mock_batch_repo, mock_batch, create_request):
    """Test successful batch creation."""
    # Arrange
    mock_batch_repo.get_by_field.return_value = None  # No existing batch
    mock_batch_repo.create.return_value = mock_batch

    # Act
    result = await batch_service.create_stock_batch(create_request)

    # Assert
    assert isinstance(result, StockBatchResponse)
    assert result.batch_id == 1
    assert result.batch_code == "BATCH-001"
    assert result.product_id == 5
    assert result.quantity_initial == 100
    assert result.quantity_current == 100

    # Verify repository calls
    mock_batch_repo.get_by_field.assert_called_once_with("batch_code", "BATCH-001")
    mock_batch_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_stock_batch_duplicate_code(batch_service, mock_batch_repo, mock_batch, create_request):
    """Test batch creation fails when batch code already exists."""
    # Arrange
    mock_batch_repo.get_by_field.return_value = mock_batch  # Existing batch

    # Act & Assert
    with pytest.raises(ValueError, match="Batch code 'BATCH-001' already exists"):
        await batch_service.create_stock_batch(create_request)

    # Verify repository calls
    mock_batch_repo.get_by_field.assert_called_once_with("batch_code", "BATCH-001")
    mock_batch_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_stock_batch_minimal_data(batch_service, mock_batch_repo):
    """Test batch creation with minimal required fields."""
    # Arrange
    minimal_batch = Mock()
    minimal_batch.batch_id = 2
    minimal_batch.batch_code = "BATCH-MIN"
    minimal_batch.current_storage_bin_id = 15
    minimal_batch.product_id = 8
    minimal_batch.quantity_initial = 50
    minimal_batch.quantity_current = 50
    minimal_batch.created_at = datetime(2025, 10, 20, 15, 0, 0)
    minimal_batch.updated_at = None

    mock_batch_repo.get_by_field.return_value = None
    mock_batch_repo.create.return_value = minimal_batch

    request = StockBatchCreateRequest(
        batch_code="BATCH-MIN",
        current_storage_bin_id=15,
        product_id=8,
        quantity_initial=50,
        quantity_current=50,
    )

    # Act
    result = await batch_service.create_stock_batch(request)

    # Assert
    assert isinstance(result, StockBatchResponse)
    assert result.batch_id == 2
    assert result.batch_code == "BATCH-MIN"
    assert result.quantity_initial == 50
    assert result.quantity_current == 50


# ============================================================================
# get_batch_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_batch_by_id_success(batch_service, mock_batch_repo, mock_batch):
    """Test successful batch retrieval by ID."""
    # Arrange
    mock_batch_repo.get.return_value = mock_batch

    # Act
    result = await batch_service.get_batch_by_id(1)

    # Assert
    assert isinstance(result, StockBatchResponse)
    assert result.batch_id == 1
    assert result.batch_code == "BATCH-001"
    assert result.product_id == 5

    # Verify repository calls
    mock_batch_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_batch_by_id_not_found(batch_service, mock_batch_repo):
    """Test batch retrieval fails when batch not found."""
    # Arrange
    mock_batch_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="Batch 999 not found"):
        await batch_service.get_batch_by_id(999)

    # Verify repository calls
    mock_batch_repo.get.assert_called_once_with(999)


# ============================================================================
# update_batch_quantity tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_batch_quantity_success(batch_service, mock_batch_repo, mock_batch):
    """Test successful batch quantity update."""
    # Arrange
    updated_batch = Mock()
    updated_batch.batch_id = 1
    updated_batch.batch_code = "BATCH-001"
    updated_batch.current_storage_bin_id = 10
    updated_batch.product_id = 5
    updated_batch.quantity_initial = 100
    updated_batch.quantity_current = 75  # Updated quantity
    updated_batch.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_batch.updated_at = datetime(2025, 10, 20, 16, 0, 0)

    mock_batch_repo.update.return_value = updated_batch

    # Act
    result = await batch_service.update_batch_quantity(batch_id=1, new_quantity=75)

    # Assert
    assert isinstance(result, StockBatchResponse)
    assert result.batch_id == 1
    assert result.quantity_current == 75

    # Verify repository calls
    mock_batch_repo.update.assert_called_once_with(1, {"quantity_current": 75})


@pytest.mark.asyncio
async def test_update_batch_quantity_to_zero(batch_service, mock_batch_repo):
    """Test updating batch quantity to zero (depleted batch)."""
    # Arrange
    depleted_batch = Mock()
    depleted_batch.batch_id = 1
    depleted_batch.batch_code = "BATCH-001"
    depleted_batch.current_storage_bin_id = 10
    depleted_batch.product_id = 5
    depleted_batch.quantity_initial = 100
    depleted_batch.quantity_current = 0  # Depleted
    depleted_batch.created_at = datetime(2025, 10, 20, 14, 30, 0)
    depleted_batch.updated_at = datetime(2025, 10, 20, 17, 0, 0)

    mock_batch_repo.update.return_value = depleted_batch

    # Act
    result = await batch_service.update_batch_quantity(batch_id=1, new_quantity=0)

    # Assert
    assert isinstance(result, StockBatchResponse)
    assert result.quantity_current == 0

    # Verify repository calls
    mock_batch_repo.update.assert_called_once_with(1, {"quantity_current": 0})


@pytest.mark.asyncio
async def test_update_batch_quantity_increase(batch_service, mock_batch_repo):
    """Test increasing batch quantity (e.g., correction)."""
    # Arrange
    increased_batch = Mock()
    increased_batch.batch_id = 1
    increased_batch.batch_code = "BATCH-001"
    increased_batch.current_storage_bin_id = 10
    increased_batch.product_id = 5
    increased_batch.quantity_initial = 100
    increased_batch.quantity_current = 150  # Increased
    increased_batch.created_at = datetime(2025, 10, 20, 14, 30, 0)
    increased_batch.updated_at = datetime(2025, 10, 20, 18, 0, 0)

    mock_batch_repo.update.return_value = increased_batch

    # Act
    result = await batch_service.update_batch_quantity(batch_id=1, new_quantity=150)

    # Assert
    assert isinstance(result, StockBatchResponse)
    assert result.quantity_current == 150

    # Verify repository calls
    mock_batch_repo.update.assert_called_once_with(1, {"quantity_current": 150})


# ============================================================================
# Edge cases
# ============================================================================


@pytest.mark.asyncio
async def test_create_stock_batch_with_zero_empty_containers(batch_service, mock_batch_repo, mock_batch):
    """Test batch creation with zero empty containers (default value)."""
    # Arrange
    mock_batch_repo.get_by_field.return_value = None
    mock_batch_repo.create.return_value = mock_batch

    request = StockBatchCreateRequest(
        batch_code="BATCH-002",
        current_storage_bin_id=10,
        product_id=5,
        quantity_initial=100,
        quantity_current=100,
        quantity_empty_containers=0,  # Explicit zero
    )

    # Act
    result = await batch_service.create_stock_batch(request)

    # Assert
    assert isinstance(result, StockBatchResponse)
    mock_batch_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_stock_batch_without_packaging(batch_service, mock_batch_repo):
    """Test batch creation without packaging (has_packaging=False)."""
    # Arrange
    no_packaging_batch = Mock()
    no_packaging_batch.batch_id = 3
    no_packaging_batch.batch_code = "BATCH-NO-PKG"
    no_packaging_batch.current_storage_bin_id = 10
    no_packaging_batch.product_id = 5
    no_packaging_batch.quantity_initial = 100
    no_packaging_batch.quantity_current = 100
    no_packaging_batch.has_packaging = False
    no_packaging_batch.created_at = datetime(2025, 10, 20, 14, 30, 0)
    no_packaging_batch.updated_at = None

    mock_batch_repo.get_by_field.return_value = None
    mock_batch_repo.create.return_value = no_packaging_batch

    request = StockBatchCreateRequest(
        batch_code="BATCH-NO-PKG",
        current_storage_bin_id=10,
        product_id=5,
        quantity_initial=100,
        quantity_current=100,
        has_packaging=False,
    )

    # Act
    result = await batch_service.create_stock_batch(request)

    # Assert
    assert isinstance(result, StockBatchResponse)
    mock_batch_repo.create.assert_called_once()
