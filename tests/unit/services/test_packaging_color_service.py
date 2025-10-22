"""Unit tests for PackagingColorService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock PackagingColorRepository
- Test CRUD operations (create, get_by_id, get_all, update, delete)
- Test hex_code field validation

Coverage target: ≥80%

Test categories:
- create: success
- get_by_id: success, not found
- get_all: success, empty list
- update: success, not found
- delete: success, not found

See:
    - Service: app/services/packaging_color_service.py
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.packaging_color_schema import (
    PackagingColorCreateRequest,
    PackagingColorResponse,
    PackagingColorUpdateRequest,
)
from app.services.packaging_color_service import PackagingColorService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_packaging_color_repo():
    """Create mock PackagingColorRepository."""
    return AsyncMock()


@pytest.fixture
def packaging_color_service(mock_packaging_color_repo):
    """Create PackagingColorService with mocked dependencies."""
    return PackagingColorService(repo=mock_packaging_color_repo)


@pytest.fixture
def mock_packaging_color():
    """Create mock PackagingColor model instance."""
    color = Mock()
    color.id = 1
    color.code = "BLACK"
    color.name = "Black"
    color.hex_code = "#000000"
    return color


# ============================================================================
# create tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_packaging_color_success(
    packaging_color_service, mock_packaging_color_repo, mock_packaging_color
):
    """Test successful packaging color creation."""
    # Arrange
    mock_packaging_color_repo.create.return_value = mock_packaging_color
    request = PackagingColorCreateRequest(code="BLACK", name="Black", hex_code="#000000")

    # Act
    result = await packaging_color_service.create(request)

    # Assert
    assert isinstance(result, PackagingColorResponse)
    assert result.id == 1
    assert result.name == "Black"
    assert result.hex_code == "#000000"
    mock_packaging_color_repo.create.assert_called_once()
    call_args = mock_packaging_color_repo.create.call_args[0][0]
    assert call_args["name"] == "Black"
    assert call_args["hex_code"] == "#000000"


# ============================================================================
# get_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(
    packaging_color_service, mock_packaging_color_repo, mock_packaging_color
):
    """Test successful retrieval by ID."""
    # Arrange
    mock_packaging_color_repo.get.return_value = mock_packaging_color

    # Act
    result = await packaging_color_service.get_by_id(1)

    # Assert
    assert isinstance(result, PackagingColorResponse)
    assert result.id == 1
    assert result.name == "Black"
    assert result.hex_code == "#000000"
    mock_packaging_color_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(packaging_color_service, mock_packaging_color_repo):
    """Test ValueError when ID not found."""
    # Arrange
    mock_packaging_color_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_color_service.get_by_id(999)

    mock_packaging_color_repo.get.assert_called_once_with(999)


# ============================================================================
# get_all tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(
    packaging_color_service, mock_packaging_color_repo, mock_packaging_color
):
    """Test successful retrieval of all packaging colors."""
    # Arrange
    mock_color_2 = Mock()
    mock_color_2.id = 2
    mock_color_2.name = "White"
    mock_color_2.hex_code = "#FFFFFF"

    mock_packaging_color_repo.get_multi.return_value = [
        mock_packaging_color,
        mock_color_2,
    ]

    # Act
    result = await packaging_color_service.get_all(limit=100)

    # Assert
    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].name == "Black"
    assert result[0].hex_code == "#000000"
    assert result[1].id == 2
    assert result[1].name == "White"
    assert result[1].hex_code == "#FFFFFF"
    mock_packaging_color_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(packaging_color_service, mock_packaging_color_repo):
    """Test get_all returns empty list when no records exist."""
    # Arrange
    mock_packaging_color_repo.get_multi.return_value = []

    # Act
    result = await packaging_color_service.get_all()

    # Assert
    assert result == []
    mock_packaging_color_repo.get_multi.assert_called_once()


# ============================================================================
# update tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_packaging_color_success(
    packaging_color_service, mock_packaging_color_repo, mock_packaging_color
):
    """Test successful packaging color update."""
    # Arrange
    updated_color = Mock()
    updated_color.id = 1
    updated_color.code = "BLACK"
    updated_color.name = "Matte Black"
    updated_color.hex_code = "#0A0A0A"

    mock_packaging_color_repo.get.return_value = mock_packaging_color
    mock_packaging_color_repo.update.return_value = updated_color

    request = PackagingColorUpdateRequest(name="Matte Black", hex_code="#0A0A0A")

    # Act
    result = await packaging_color_service.update(1, request)

    # Assert
    assert isinstance(result, PackagingColorResponse)
    assert result.id == 1
    assert result.name == "Matte Black"
    assert result.hex_code == "#0A0A0A"
    mock_packaging_color_repo.get.assert_called_once_with(1)
    mock_packaging_color_repo.update.assert_called_once()
    call_args = mock_packaging_color_repo.update.call_args[0]
    assert call_args[0] == 1
    assert call_args[1]["name"] == "Matte Black"
    assert call_args[1]["hex_code"] == "#0A0A0A"


@pytest.mark.asyncio
async def test_update_packaging_color_not_found(packaging_color_service, mock_packaging_color_repo):
    """Test ValueError when updating non-existent packaging color."""
    # Arrange
    mock_packaging_color_repo.get.return_value = None
    request = PackagingColorUpdateRequest(name="Updated")

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_color_service.update(999, request)

    mock_packaging_color_repo.get.assert_called_once_with(999)
    mock_packaging_color_repo.update.assert_not_called()


# ============================================================================
# delete tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_packaging_color_success(
    packaging_color_service, mock_packaging_color_repo, mock_packaging_color
):
    """Test successful packaging color deletion."""
    # Arrange
    mock_packaging_color_repo.get.return_value = mock_packaging_color
    mock_packaging_color_repo.delete.return_value = None

    # Act
    result = await packaging_color_service.delete(1)

    # Assert
    assert result is None
    mock_packaging_color_repo.get.assert_called_once_with(1)
    mock_packaging_color_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_packaging_color_not_found(packaging_color_service, mock_packaging_color_repo):
    """Test ValueError when deleting non-existent packaging color."""
    # Arrange
    mock_packaging_color_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_color_service.delete(999)

    mock_packaging_color_repo.get.assert_called_once_with(999)
    mock_packaging_color_repo.delete.assert_not_called()
