"""Unit tests for PriceListService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock for PriceListRepository.

Coverage target: ≥85%

Test categories:
- create: success, minimal fields, validation
- get_by_id: success, not found
- get_all: empty, multiple records, limit
- update: success, not found, partial
- delete: success, not found

See:
    - Service: app/services/price_list_service.py
    - Model: app/models/price_list.py
    - Schema: app/schemas/price_list_schema.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.price_list import PriceList
from app.schemas.price_list_schema import (
    PriceListCreateRequest,
    PriceListResponse,
    PriceListUpdateRequest,
)
from app.services.price_list_service import PriceListService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo():
    """Create mock PriceListRepository for testing."""
    return AsyncMock()


@pytest.fixture
def price_list_service(mock_repo):
    """Create PriceListService with mocked repository."""
    return PriceListService(repo=mock_repo)


@pytest.fixture
def mock_price_list():
    """Create mock PriceList model instance."""
    price = Mock(spec=PriceList)
    price.price_list_id = 1
    price.code = "POT-10L-CACTUS"
    price.name = "10L Pot - Cactus"
    price.price_per_unit = 12.50
    price.currency = "USD"
    price.created_at = datetime(2025, 10, 20, 14, 30, 0)
    price.updated_at = None
    return price


# ============================================================================
# Test Create
# ============================================================================


@pytest.mark.asyncio
async def test_create_success(price_list_service, mock_repo, mock_price_list):
    """Test successful price list creation."""
    # Arrange
    request = PriceListCreateRequest(
        code="POT-10L-CACTUS",
        name="10L Pot - Cactus",
        price_per_unit=12.50,
        currency="USD",
    )

    mock_repo.create.return_value = mock_price_list

    # Act
    response = await price_list_service.create(request)

    # Assert
    assert isinstance(response, PriceListResponse)
    assert response.price_list_id == 1
    assert response.code == "POT-10L-CACTUS"
    assert response.name == "10L Pot - Cactus"
    assert response.price_per_unit == 12.50
    assert response.currency == "USD"
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_default_currency(price_list_service, mock_repo):
    """Test creating price list with default USD currency."""
    # Arrange
    request = PriceListCreateRequest(
        code="POT-15L-SUCC",
        name="15L Pot - Succulent",
        price_per_unit=18.75,
    )

    mock_default = Mock(spec=PriceList)
    mock_default.price_list_id = 2
    mock_default.code = "POT-15L-SUCC"
    mock_default.name = "15L Pot - Succulent"
    mock_default.price_per_unit = 18.75
    mock_default.currency = "USD"  # Default
    mock_default.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_default.updated_at = None

    mock_repo.create.return_value = mock_default

    # Act
    response = await price_list_service.create(request)

    # Assert
    assert response.currency == "USD"


@pytest.mark.asyncio
async def test_create_with_custom_currency(price_list_service, mock_repo):
    """Test creating price list with custom currency."""
    # Arrange
    request = PriceListCreateRequest(
        code="POT-20L-ORCH",
        name="20L Pot - Orchid",
        price_per_unit=25.00,
        currency="EUR",
    )

    mock_eur = Mock(spec=PriceList)
    mock_eur.price_list_id = 3
    mock_eur.code = "POT-20L-ORCH"
    mock_eur.name = "20L Pot - Orchid"
    mock_eur.price_per_unit = 25.00
    mock_eur.currency = "EUR"
    mock_eur.created_at = datetime(2025, 10, 20, 15, 30, 0)
    mock_eur.updated_at = None

    mock_repo.create.return_value = mock_eur

    # Act
    response = await price_list_service.create(request)

    # Assert
    assert response.currency == "EUR"


# ============================================================================
# Test Get By ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(price_list_service, mock_repo, mock_price_list):
    """Test getting price list by ID successfully."""
    # Arrange
    mock_repo.get.return_value = mock_price_list

    # Act
    response = await price_list_service.get_by_id(1)

    # Assert
    assert response.price_list_id == 1
    assert response.code == "POT-10L-CACTUS"
    assert response.price_per_unit == 12.50
    mock_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(price_list_service, mock_repo):
    """Test getting non-existent price list raises ValueError."""
    # Arrange
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="PriceList"):
        await price_list_service.get_by_id(999)


# ============================================================================
# Test Get All
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(price_list_service, mock_repo):
    """Test getting all price lists."""
    # Arrange
    mock_price1 = Mock(spec=PriceList)
    mock_price1.price_list_id = 1
    mock_price1.code = "POT-10L-CACTUS"
    mock_price1.name = "10L Pot - Cactus"
    mock_price1.price_per_unit = 12.50
    mock_price1.currency = "USD"
    mock_price1.created_at = datetime(2025, 10, 20, 14, 0, 0)
    mock_price1.updated_at = None

    mock_price2 = Mock(spec=PriceList)
    mock_price2.price_list_id = 2
    mock_price2.code = "POT-15L-SUCC"
    mock_price2.name = "15L Pot - Succulent"
    mock_price2.price_per_unit = 18.75
    mock_price2.currency = "USD"
    mock_price2.created_at = datetime(2025, 10, 20, 14, 30, 0)
    mock_price2.updated_at = None

    mock_repo.get_multi.return_value = [mock_price1, mock_price2]

    # Act
    response = await price_list_service.get_all()

    # Assert
    assert len(response) == 2
    assert response[0].code == "POT-10L-CACTUS"
    assert response[1].code == "POT-15L-SUCC"
    mock_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(price_list_service, mock_repo):
    """Test getting price lists when none exist."""
    # Arrange
    mock_repo.get_multi.return_value = []

    # Act
    response = await price_list_service.get_all()

    # Assert
    assert len(response) == 0


@pytest.mark.asyncio
async def test_get_all_with_custom_limit(price_list_service, mock_repo):
    """Test getting price lists with custom limit."""
    # Arrange
    mock_repo.get_multi.return_value = []

    # Act
    await price_list_service.get_all(limit=50)

    # Assert
    mock_repo.get_multi.assert_called_once_with(limit=50)


# ============================================================================
# Test Update
# ============================================================================


@pytest.mark.asyncio
async def test_update_success(price_list_service, mock_repo, mock_price_list):
    """Test updating price list successfully."""
    # Arrange
    request = PriceListUpdateRequest(name="Updated Name", price_per_unit=15.00)

    updated_mock = Mock(spec=PriceList)
    updated_mock.price_list_id = 1
    updated_mock.code = "POT-10L-CACTUS"  # Code unchanged
    updated_mock.name = "Updated Name"
    updated_mock.price_per_unit = 15.00
    updated_mock.currency = "USD"
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_repo.get.return_value = mock_price_list
    mock_repo.update.return_value = updated_mock

    # Act
    response = await price_list_service.update(1, request)

    # Assert
    assert response.name == "Updated Name"
    assert response.price_per_unit == 15.00
    assert response.updated_at is not None
    mock_repo.get.assert_called_once_with(1)
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_not_found(price_list_service, mock_repo):
    """Test updating non-existent price list raises ValueError."""
    # Arrange
    request = PriceListUpdateRequest(name="Updated Name")
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="PriceList"):
        await price_list_service.update(999, request)


@pytest.mark.asyncio
async def test_update_partial_name_only(price_list_service, mock_repo, mock_price_list):
    """Test partial update (only name, no price)."""
    # Arrange
    request = PriceListUpdateRequest(name="New Name Only")

    updated_mock = Mock(spec=PriceList)
    updated_mock.price_list_id = 1
    updated_mock.code = "POT-10L-CACTUS"
    updated_mock.name = "New Name Only"
    updated_mock.price_per_unit = 12.50  # Unchanged
    updated_mock.currency = "USD"
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_repo.get.return_value = mock_price_list
    mock_repo.update.return_value = updated_mock

    # Act
    response = await price_list_service.update(1, request)

    # Assert
    assert response.name == "New Name Only"
    assert response.price_per_unit == 12.50  # Unchanged
    call_args = mock_repo.update.call_args
    assert "name" in call_args[0][1]


@pytest.mark.asyncio
async def test_update_partial_price_only(price_list_service, mock_repo, mock_price_list):
    """Test partial update (only price, no name)."""
    # Arrange
    request = PriceListUpdateRequest(price_per_unit=20.00)

    updated_mock = Mock(spec=PriceList)
    updated_mock.price_list_id = 1
    updated_mock.code = "POT-10L-CACTUS"
    updated_mock.name = "10L Pot - Cactus"  # Unchanged
    updated_mock.price_per_unit = 20.00
    updated_mock.currency = "USD"
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_repo.get.return_value = mock_price_list
    mock_repo.update.return_value = updated_mock

    # Act
    response = await price_list_service.update(1, request)

    # Assert
    assert response.name == "10L Pot - Cactus"  # Unchanged
    assert response.price_per_unit == 20.00
    call_args = mock_repo.update.call_args
    assert "price_per_unit" in call_args[0][1]


# ============================================================================
# Test Delete
# ============================================================================


@pytest.mark.asyncio
async def test_delete_success(price_list_service, mock_repo, mock_price_list):
    """Test deleting price list successfully."""
    # Arrange
    mock_repo.get.return_value = mock_price_list
    mock_repo.delete.return_value = None

    # Act
    await price_list_service.delete(1)

    # Assert
    mock_repo.get.assert_called_once_with(1)
    mock_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_not_found(price_list_service, mock_repo):
    """Test deleting non-existent price list raises ValueError."""
    # Arrange
    mock_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="PriceList"):
        await price_list_service.delete(999)
