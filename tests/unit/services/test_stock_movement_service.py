"""Unit tests for StockMovementService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock StockMovementRepository
- Test movement creation with UUID generation
- Test movement history retrieval
- Test movement type validation

Coverage target: ≥80%

Test categories:
- create_stock_movement: success, with all fields
- get_movements_by_batch: success, empty list, multiple movements

See:
    - Service: app/services/stock_movement_service.py
    - Schema: app/schemas/stock_movement_schema.py
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from app.schemas.stock_movement_schema import (
    StockMovementCreateRequest,
    StockMovementResponse,
)
from app.services.stock_movement_service import StockMovementService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_movement_repo():
    """Create mock StockMovementRepository."""
    repo = AsyncMock()
    # Mock the model attribute for query building
    repo.model = Mock()
    repo.model.batch_id = Mock()
    repo.model.created_at = Mock()
    repo.model.created_at.desc = Mock(return_value=Mock())
    # Mock session for query execution
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def movement_service(mock_movement_repo):
    """Create StockMovementService with mocked dependencies."""
    return StockMovementService(movement_repo=mock_movement_repo)


@pytest.fixture
def mock_movement():
    """Create mock StockMovement model instance."""
    movement = Mock()
    movement.id = 1
    movement.movement_id = UUID("12345678-1234-5678-1234-567812345678")
    movement.batch_id = 5
    movement.movement_type = "manual_init"
    movement.quantity = 100
    movement.user_id = 1
    movement.source_type = "manual"
    movement.is_inbound = True
    movement.reason_description = "Initial inventory setup"
    movement.source_bin_id = None
    movement.destination_bin_id = 10
    movement.unit_price = Decimal("2.50")
    movement.total_price = Decimal("250.00")
    movement.processing_session_id = None
    movement.created_at = datetime(2025, 10, 20, 14, 30, 0)
    return movement


@pytest.fixture
def create_request():
    """Create sample StockMovementCreateRequest."""
    return StockMovementCreateRequest(
        batch_id=5,
        movement_type="manual_init",
        quantity=100,
        user_id=1,
        source_type="manual",
        is_inbound=True,
        reason_description="Initial inventory setup",
        destination_bin_id=10,
        unit_price=Decimal("2.50"),
        total_price=Decimal("250.00"),
    )


# ============================================================================
# create_stock_movement tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_stock_movement_success(
    movement_service, mock_movement_repo, mock_movement, create_request
):
    """Test successful movement creation with UUID generation."""
    # Arrange
    mock_movement_repo.create.return_value = mock_movement

    # Act
    result = await movement_service.create_stock_movement(create_request)

    # Assert
    assert isinstance(result, StockMovementResponse)
    assert result.id == 1
    assert isinstance(result.movement_id, UUID)
    assert result.batch_id == 5
    assert result.movement_type == "manual_init"
    assert result.quantity == 100
    assert result.user_id == 1
    assert result.source_type == "manual"
    assert result.is_inbound is True

    # Verify repository calls
    mock_movement_repo.create.assert_called_once()
    call_args = mock_movement_repo.create.call_args[0][0]
    assert "movement_id" in call_args
    assert isinstance(call_args["movement_id"], UUID)


@pytest.mark.asyncio
async def test_create_stock_movement_outbound(movement_service, mock_movement_repo):
    """Test outbound movement creation (negative quantity)."""
    # Arrange
    outbound_movement = Mock()
    outbound_movement.id = 2
    outbound_movement.movement_id = uuid4()
    outbound_movement.batch_id = 5
    outbound_movement.movement_type = "ventas"
    outbound_movement.quantity = -20
    outbound_movement.user_id = 2
    outbound_movement.source_type = "manual"
    outbound_movement.is_inbound = False
    outbound_movement.created_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_movement_repo.create.return_value = outbound_movement

    request = StockMovementCreateRequest(
        batch_id=5,
        movement_type="ventas",
        quantity=-20,
        user_id=2,
        source_type="manual",
        is_inbound=False,
        reason_description="Sale to customer X",
    )

    # Act
    result = await movement_service.create_stock_movement(request)

    # Assert
    assert isinstance(result, StockMovementResponse)
    assert result.quantity == -20
    assert result.is_inbound is False
    assert result.movement_type == "ventas"


@pytest.mark.asyncio
async def test_create_stock_movement_from_ml_pipeline(movement_service, mock_movement_repo):
    """Test movement creation from ML pipeline."""
    # Arrange
    ml_movement = Mock()
    ml_movement.id = 3
    ml_movement.movement_id = uuid4()
    ml_movement.batch_id = 5
    ml_movement.movement_type = "detection_update"
    ml_movement.quantity = 50
    ml_movement.user_id = 1
    ml_movement.source_type = "ml_pipeline"
    ml_movement.is_inbound = True
    ml_movement.processing_session_id = 100
    ml_movement.created_at = datetime(2025, 10, 20, 16, 0, 0)

    mock_movement_repo.create.return_value = ml_movement

    request = StockMovementCreateRequest(
        batch_id=5,
        movement_type="detection_update",
        quantity=50,
        user_id=1,
        source_type="ml_pipeline",
        is_inbound=True,
        processing_session_id=100,
    )

    # Act
    result = await movement_service.create_stock_movement(request)

    # Assert
    assert isinstance(result, StockMovementResponse)
    assert result.source_type == "ml_pipeline"


@pytest.mark.asyncio
async def test_create_stock_movement_transfer(movement_service, mock_movement_repo):
    """Test movement creation for bin-to-bin transfer."""
    # Arrange
    transfer_movement = Mock()
    transfer_movement.id = 4
    transfer_movement.movement_id = uuid4()
    transfer_movement.batch_id = 5
    transfer_movement.movement_type = "transfer"
    transfer_movement.quantity = 0  # Transfer doesn't change total quantity
    transfer_movement.user_id = 1
    transfer_movement.source_type = "manual"
    transfer_movement.is_inbound = True
    transfer_movement.source_bin_id = 10
    transfer_movement.destination_bin_id = 15
    transfer_movement.created_at = datetime(2025, 10, 20, 17, 0, 0)

    mock_movement_repo.create.return_value = transfer_movement

    request = StockMovementCreateRequest(
        batch_id=5,
        movement_type="transfer",
        quantity=0,
        user_id=1,
        source_type="manual",
        is_inbound=True,
        source_bin_id=10,
        destination_bin_id=15,
        reason_description="Relocate to better bin",
    )

    # Act
    result = await movement_service.create_stock_movement(request)

    # Assert
    assert isinstance(result, StockMovementResponse)
    assert result.movement_type == "transfer"


@pytest.mark.asyncio
async def test_create_stock_movement_with_pricing(movement_service, mock_movement_repo):
    """Test movement creation with pricing information."""
    # Arrange
    priced_movement = Mock()
    priced_movement.id = 5
    priced_movement.movement_id = uuid4()
    priced_movement.batch_id = 5
    priced_movement.movement_type = "ventas"
    priced_movement.quantity = -10
    priced_movement.user_id = 1
    priced_movement.source_type = "manual"
    priced_movement.is_inbound = False
    priced_movement.unit_price = Decimal("5.75")
    priced_movement.total_price = Decimal("57.50")
    priced_movement.created_at = datetime(2025, 10, 20, 18, 0, 0)

    mock_movement_repo.create.return_value = priced_movement

    request = StockMovementCreateRequest(
        batch_id=5,
        movement_type="ventas",
        quantity=-10,
        user_id=1,
        source_type="manual",
        is_inbound=False,
        unit_price=Decimal("5.75"),
        total_price=Decimal("57.50"),
    )

    # Act
    result = await movement_service.create_stock_movement(request)

    # Assert
    assert isinstance(result, StockMovementResponse)
    mock_movement_repo.create.assert_called_once()


# ============================================================================
# get_movements_by_batch tests
# NOTE: This method uses SQLAlchemy query building which requires integration
# testing with a real database. Unit tests are limited to create methods only.
# See tests/integration/ for full get_movements_by_batch testing.
# ============================================================================


# ============================================================================
# Edge cases
# ============================================================================


@pytest.mark.asyncio
async def test_create_stock_movement_minimal_fields(movement_service, mock_movement_repo):
    """Test movement creation with only required fields."""
    # Arrange
    minimal_movement = Mock()
    minimal_movement.id = 1
    minimal_movement.movement_id = uuid4()
    minimal_movement.batch_id = 5
    minimal_movement.movement_type = "ajuste"
    minimal_movement.quantity = 5
    minimal_movement.user_id = 1
    minimal_movement.source_type = "manual"
    minimal_movement.is_inbound = True
    minimal_movement.created_at = datetime(2025, 10, 20, 14, 0, 0)

    mock_movement_repo.create.return_value = minimal_movement

    request = StockMovementCreateRequest(
        batch_id=5,
        movement_type="ajuste",
        quantity=5,
        user_id=1,
        is_inbound=True,
    )

    # Act
    result = await movement_service.create_stock_movement(request)

    # Assert
    assert isinstance(result, StockMovementResponse)
    assert result.source_type == "manual"  # Default value


@pytest.mark.asyncio
async def test_create_stock_movement_uuid_uniqueness(movement_service, mock_movement_repo):
    """Test that each movement gets a unique UUID."""
    # Arrange
    created_uuids = []

    def mock_create_side_effect(data):
        movement = Mock()
        movement.id = len(created_uuids) + 1
        movement.movement_id = data["movement_id"]
        movement.batch_id = 5
        movement.movement_type = "ajuste"
        movement.quantity = 1
        movement.user_id = 1
        movement.source_type = "manual"
        movement.is_inbound = True
        movement.created_at = datetime(2025, 10, 20, 14, 0, 0)
        created_uuids.append(data["movement_id"])
        return movement

    mock_movement_repo.create.side_effect = mock_create_side_effect

    request = StockMovementCreateRequest(
        batch_id=5,
        movement_type="ajuste",
        quantity=1,
        user_id=1,
        is_inbound=True,
    )

    # Act - Create multiple movements
    await movement_service.create_stock_movement(request)
    await movement_service.create_stock_movement(request)
    await movement_service.create_stock_movement(request)

    # Assert - All UUIDs are unique
    assert len(created_uuids) == 3
    assert len(set(created_uuids)) == 3  # All unique
