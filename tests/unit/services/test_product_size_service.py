"""Unit tests for ProductSizeService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock ProductSizeRepository
- Test CRUD operations (create, get_by_id, get_all, update, delete)
- Test height range fields (min_height_cm, max_height_cm)

Coverage target: ≥80%

Test categories:
- create: success, with height ranges
- get_by_id: success, not found
- get_all: success, empty list
- update: success, not found
- delete: success, not found

See:
    - Service: app/services/product_size_service.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.product_size_schema import (
    ProductSizeCreateRequest,
    ProductSizeResponse,
    ProductSizeUpdateRequest,
)
from app.services.product_size_service import ProductSizeService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_product_size_repo():
    """Create mock ProductSizeRepository."""
    return AsyncMock()


@pytest.fixture
def product_size_service(mock_product_size_repo):
    """Create ProductSizeService with mocked dependencies."""
    return ProductSizeService(repo=mock_product_size_repo)


@pytest.fixture
def mock_product_size():
    """Create mock ProductSize model instance."""
    size = Mock()
    size.product_size_id = 1
    size.code = "M"
    size.name = "Medium"
    size.min_height_cm = 20.0
    size.max_height_cm = 40.0
    size.created_at = datetime(2025, 10, 20, 14, 30, 0)
    size.updated_at = None
    return size


# ============================================================================
# create tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_product_size_success(
    product_size_service, mock_product_size_repo, mock_product_size
):
    """Test successful product size creation with height ranges."""
    # Arrange
    mock_product_size_repo.create.return_value = mock_product_size
    request = ProductSizeCreateRequest(
        code="M", name="Medium", min_height_cm=20.0, max_height_cm=40.0
    )

    # Act
    result = await product_size_service.create(request)

    # Assert
    assert isinstance(result, ProductSizeResponse)
    assert result.product_size_id == 1
    assert result.code == "M"
    assert result.name == "Medium"
    assert result.min_height_cm == 20.0
    assert result.max_height_cm == 40.0
    mock_product_size_repo.create.assert_called_once()
    call_args = mock_product_size_repo.create.call_args[0][0]
    assert call_args["code"] == "M"
    assert call_args["name"] == "Medium"
    assert call_args["min_height_cm"] == 20.0
    assert call_args["max_height_cm"] == 40.0


@pytest.mark.asyncio
async def test_create_product_size_small(product_size_service, mock_product_size_repo):
    """Test creating small size product."""
    # Arrange
    mock_size = Mock()
    mock_size.product_size_id = 2
    mock_size.code = "S"
    mock_size.name = "Small"
    mock_size.min_height_cm = 10.0
    mock_size.max_height_cm = 20.0
    mock_size.created_at = datetime(2025, 10, 20, 14, 30, 0)
    mock_size.updated_at = None

    mock_product_size_repo.create.return_value = mock_size
    request = ProductSizeCreateRequest(
        code="S", name="Small", min_height_cm=10.0, max_height_cm=20.0
    )

    # Act
    result = await product_size_service.create(request)

    # Assert
    assert result.product_size_id == 2
    assert result.code == "S"
    assert result.min_height_cm == 10.0
    assert result.max_height_cm == 20.0


# ============================================================================
# get_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(
    product_size_service, mock_product_size_repo, mock_product_size
):
    """Test successful retrieval by ID."""
    # Arrange
    mock_product_size_repo.get.return_value = mock_product_size

    # Act
    result = await product_size_service.get_by_id(1)

    # Assert
    assert isinstance(result, ProductSizeResponse)
    assert result.product_size_id == 1
    assert result.code == "M"
    assert result.name == "Medium"
    assert result.min_height_cm == 20.0
    assert result.max_height_cm == 40.0
    mock_product_size_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(product_size_service, mock_product_size_repo):
    """Test ValueError when ID not found."""
    # Arrange
    mock_product_size_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await product_size_service.get_by_id(999)

    mock_product_size_repo.get.assert_called_once_with(999)


# ============================================================================
# get_all tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(product_size_service, mock_product_size_repo, mock_product_size):
    """Test successful retrieval of all product sizes."""
    # Arrange
    mock_size_2 = Mock()
    mock_size_2.product_size_id = 2
    mock_size_2.code = "L"
    mock_size_2.name = "Large"
    mock_size_2.min_height_cm = 40.0
    mock_size_2.max_height_cm = 60.0
    mock_size_2.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_size_2.updated_at = None

    mock_product_size_repo.get_multi.return_value = [mock_product_size, mock_size_2]

    # Act
    result = await product_size_service.get_all(limit=100)

    # Assert
    assert len(result) == 2
    assert result[0].product_size_id == 1
    assert result[0].code == "M"
    assert result[0].min_height_cm == 20.0
    assert result[0].max_height_cm == 40.0
    assert result[1].product_size_id == 2
    assert result[1].code == "L"
    assert result[1].min_height_cm == 40.0
    assert result[1].max_height_cm == 60.0
    mock_product_size_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(product_size_service, mock_product_size_repo):
    """Test get_all returns empty list when no records exist."""
    # Arrange
    mock_product_size_repo.get_multi.return_value = []

    # Act
    result = await product_size_service.get_all()

    # Assert
    assert result == []
    mock_product_size_repo.get_multi.assert_called_once()


# ============================================================================
# update tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_product_size_success(
    product_size_service, mock_product_size_repo, mock_product_size
):
    """Test successful product size update."""
    # Arrange
    updated_size = Mock()
    updated_size.product_size_id = 1
    updated_size.code = "M"
    updated_size.name = "Medium - Standard"
    updated_size.min_height_cm = 25.0
    updated_size.max_height_cm = 45.0
    updated_size.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_size.updated_at = datetime(2025, 10, 20, 16, 0, 0)

    mock_product_size_repo.get.return_value = mock_product_size
    mock_product_size_repo.update.return_value = updated_size

    request = ProductSizeUpdateRequest(
        name="Medium - Standard", min_height_cm=25.0, max_height_cm=45.0
    )

    # Act
    result = await product_size_service.update(1, request)

    # Assert
    assert isinstance(result, ProductSizeResponse)
    assert result.product_size_id == 1
    assert result.name == "Medium - Standard"
    assert result.min_height_cm == 25.0
    assert result.max_height_cm == 45.0
    mock_product_size_repo.get.assert_called_once_with(1)
    mock_product_size_repo.update.assert_called_once()
    call_args = mock_product_size_repo.update.call_args[0]
    assert call_args[0] == 1
    assert call_args[1]["name"] == "Medium - Standard"
    assert call_args[1]["min_height_cm"] == 25.0
    assert call_args[1]["max_height_cm"] == 45.0


@pytest.mark.asyncio
async def test_update_product_size_not_found(product_size_service, mock_product_size_repo):
    """Test ValueError when updating non-existent product size."""
    # Arrange
    mock_product_size_repo.get.return_value = None
    request = ProductSizeUpdateRequest(name="Updated")

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await product_size_service.update(999, request)

    mock_product_size_repo.get.assert_called_once_with(999)
    mock_product_size_repo.update.assert_not_called()


# ============================================================================
# delete tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_product_size_success(
    product_size_service, mock_product_size_repo, mock_product_size
):
    """Test successful product size deletion."""
    # Arrange
    mock_product_size_repo.get.return_value = mock_product_size
    mock_product_size_repo.delete.return_value = None

    # Act
    result = await product_size_service.delete(1)

    # Assert
    assert result is None
    mock_product_size_repo.get.assert_called_once_with(1)
    mock_product_size_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_product_size_not_found(product_size_service, mock_product_size_repo):
    """Test ValueError when deleting non-existent product size."""
    # Arrange
    mock_product_size_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await product_size_service.delete(999)

    mock_product_size_repo.get.assert_called_once_with(999)
    mock_product_size_repo.delete.assert_not_called()
