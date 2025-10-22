"""Unit tests for ProductStateService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock ProductStateRepository
- Test CRUD operations (create, get_by_id, get_all, update, delete)
- Test is_sellable field handling

Coverage target: ≥80%

Test categories:
- create: success, with is_sellable flag
- get_by_id: success, not found
- get_all: success, empty list
- update: success, not found
- delete: success, not found

See:
    - Service: app/services/product_state_service.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.product_state_schema import (
    ProductStateCreateRequest,
    ProductStateResponse,
    ProductStateUpdateRequest,
)
from app.services.product_state_service import ProductStateService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_product_state_repo():
    """Create mock ProductStateRepository."""
    return AsyncMock()


@pytest.fixture
def product_state_service(mock_product_state_repo):
    """Create ProductStateService with mocked dependencies."""
    return ProductStateService(repo=mock_product_state_repo)


@pytest.fixture
def mock_product_state():
    """Create mock ProductState model instance."""
    state = Mock()
    state.product_state_id = 1
    state.code = "READY"
    state.name = "Ready to Sell"
    state.is_sellable = True
    state.created_at = datetime(2025, 10, 20, 14, 30, 0)
    state.updated_at = None
    return state


# ============================================================================
# create tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_product_state_success(
    product_state_service, mock_product_state_repo, mock_product_state
):
    """Test successful product state creation with is_sellable flag."""
    # Arrange
    mock_product_state_repo.create.return_value = mock_product_state
    request = ProductStateCreateRequest(code="READY", name="Ready to Sell", is_sellable=True)

    # Act
    result = await product_state_service.create(request)

    # Assert
    assert isinstance(result, ProductStateResponse)
    assert result.product_state_id == 1
    assert result.code == "READY"
    assert result.name == "Ready to Sell"
    assert result.is_sellable is True
    mock_product_state_repo.create.assert_called_once()
    call_args = mock_product_state_repo.create.call_args[0][0]
    assert call_args["code"] == "READY"
    assert call_args["name"] == "Ready to Sell"
    assert call_args["is_sellable"] is True


@pytest.mark.asyncio
async def test_create_product_state_not_sellable(product_state_service, mock_product_state_repo):
    """Test creating product state with is_sellable=False."""
    # Arrange
    mock_state = Mock()
    mock_state.product_state_id = 2
    mock_state.code = "GROWING"
    mock_state.name = "Growing"
    mock_state.is_sellable = False
    mock_state.created_at = datetime(2025, 10, 20, 14, 30, 0)
    mock_state.updated_at = None

    mock_product_state_repo.create.return_value = mock_state
    request = ProductStateCreateRequest(code="GROWING", name="Growing", is_sellable=False)

    # Act
    result = await product_state_service.create(request)

    # Assert
    assert result.product_state_id == 2
    assert result.code == "GROWING"
    assert result.is_sellable is False


# ============================================================================
# get_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(
    product_state_service, mock_product_state_repo, mock_product_state
):
    """Test successful retrieval by ID."""
    # Arrange
    mock_product_state_repo.get.return_value = mock_product_state

    # Act
    result = await product_state_service.get_by_id(1)

    # Assert
    assert isinstance(result, ProductStateResponse)
    assert result.product_state_id == 1
    assert result.code == "READY"
    assert result.name == "Ready to Sell"
    assert result.is_sellable is True
    mock_product_state_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(product_state_service, mock_product_state_repo):
    """Test ValueError when ID not found."""
    # Arrange
    mock_product_state_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await product_state_service.get_by_id(999)

    mock_product_state_repo.get.assert_called_once_with(999)


# ============================================================================
# get_all tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(product_state_service, mock_product_state_repo, mock_product_state):
    """Test successful retrieval of all product states."""
    # Arrange
    mock_state_2 = Mock()
    mock_state_2.product_state_id = 2
    mock_state_2.code = "GROWING"
    mock_state_2.name = "Growing"
    mock_state_2.is_sellable = False
    mock_state_2.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_state_2.updated_at = None

    mock_product_state_repo.get_multi.return_value = [mock_product_state, mock_state_2]

    # Act
    result = await product_state_service.get_all(limit=100)

    # Assert
    assert len(result) == 2
    assert result[0].product_state_id == 1
    assert result[0].code == "READY"
    assert result[0].is_sellable is True
    assert result[1].product_state_id == 2
    assert result[1].code == "GROWING"
    assert result[1].is_sellable is False
    mock_product_state_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(product_state_service, mock_product_state_repo):
    """Test get_all returns empty list when no records exist."""
    # Arrange
    mock_product_state_repo.get_multi.return_value = []

    # Act
    result = await product_state_service.get_all()

    # Assert
    assert result == []
    mock_product_state_repo.get_multi.assert_called_once()


# ============================================================================
# update tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_product_state_success(
    product_state_service, mock_product_state_repo, mock_product_state
):
    """Test successful product state update."""
    # Arrange
    updated_state = Mock()
    updated_state.product_state_id = 1
    updated_state.code = "READY"
    updated_state.name = "Ready for Sale"
    updated_state.is_sellable = True
    updated_state.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_state.updated_at = datetime(2025, 10, 20, 16, 0, 0)

    mock_product_state_repo.get.return_value = mock_product_state
    mock_product_state_repo.update.return_value = updated_state

    request = ProductStateUpdateRequest(name="Ready for Sale")

    # Act
    result = await product_state_service.update(1, request)

    # Assert
    assert isinstance(result, ProductStateResponse)
    assert result.product_state_id == 1
    assert result.name == "Ready for Sale"
    mock_product_state_repo.get.assert_called_once_with(1)
    mock_product_state_repo.update.assert_called_once()
    call_args = mock_product_state_repo.update.call_args[0]
    assert call_args[0] == 1
    assert call_args[1]["name"] == "Ready for Sale"


@pytest.mark.asyncio
async def test_update_product_state_not_found(product_state_service, mock_product_state_repo):
    """Test ValueError when updating non-existent product state."""
    # Arrange
    mock_product_state_repo.get.return_value = None
    request = ProductStateUpdateRequest(name="Updated")

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await product_state_service.update(999, request)

    mock_product_state_repo.get.assert_called_once_with(999)
    mock_product_state_repo.update.assert_not_called()


# ============================================================================
# delete tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_product_state_success(
    product_state_service, mock_product_state_repo, mock_product_state
):
    """Test successful product state deletion."""
    # Arrange
    mock_product_state_repo.get.return_value = mock_product_state
    mock_product_state_repo.delete.return_value = None

    # Act
    result = await product_state_service.delete(1)

    # Assert
    assert result is None
    mock_product_state_repo.get.assert_called_once_with(1)
    mock_product_state_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_product_state_not_found(product_state_service, mock_product_state_repo):
    """Test ValueError when deleting non-existent product state."""
    # Arrange
    mock_product_state_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await product_state_service.delete(999)

    mock_product_state_repo.get.assert_called_once_with(999)
    mock_product_state_repo.delete.assert_not_called()
