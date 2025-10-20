"""Unit tests for DensityParameterService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock DensityParameterRepository
- Test CRUD operations (create, get_by_id, get_all, update, delete)
- Test ML density parameters (plants_per_m2, confidence_threshold)

Coverage target: ≥80%

Test categories:
- create: success, with density parameters
- get_by_id: success, not found
- get_all: success, empty list
- update: success, not found
- delete: success, not found

See:
    - Service: app/services/density_parameter_service.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.density_parameter_schema import (
    DensityParameterCreateRequest,
    DensityParameterResponse,
    DensityParameterUpdateRequest,
)
from app.services.density_parameter_service import DensityParameterService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_density_parameter_repo():
    """Create mock DensityParameterRepository."""
    return AsyncMock()


@pytest.fixture
def density_parameter_service(mock_density_parameter_repo):
    """Create DensityParameterService with mocked dependencies."""
    return DensityParameterService(repo=mock_density_parameter_repo)


@pytest.fixture
def mock_density_parameter():
    """Create mock DensityParameter model instance."""
    param = Mock()
    param.density_parameter_id = 1
    param.name = "High Density - Geraniums"
    param.plants_per_m2 = 25.5
    param.confidence_threshold = 0.8
    param.created_at = datetime(2025, 10, 20, 14, 30, 0)
    param.updated_at = None
    return param


# ============================================================================
# create tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_density_parameter_success(
    density_parameter_service, mock_density_parameter_repo, mock_density_parameter
):
    """Test successful density parameter creation."""
    # Arrange
    mock_density_parameter_repo.create.return_value = mock_density_parameter
    request = DensityParameterCreateRequest(
        name="High Density - Geraniums", plants_per_m2=25.5, confidence_threshold=0.8
    )

    # Act
    result = await density_parameter_service.create(request)

    # Assert
    assert isinstance(result, DensityParameterResponse)
    assert result.density_parameter_id == 1
    assert result.name == "High Density - Geraniums"
    assert result.plants_per_m2 == 25.5
    assert result.confidence_threshold == 0.8
    mock_density_parameter_repo.create.assert_called_once()
    call_args = mock_density_parameter_repo.create.call_args[0][0]
    assert call_args["name"] == "High Density - Geraniums"
    assert call_args["plants_per_m2"] == 25.5
    assert call_args["confidence_threshold"] == 0.8


@pytest.mark.asyncio
async def test_create_density_parameter_default_threshold(
    density_parameter_service, mock_density_parameter_repo
):
    """Test creating density parameter with default confidence threshold."""
    # Arrange
    mock_param = Mock()
    mock_param.density_parameter_id = 2
    mock_param.name = "Low Density - Ficus"
    mock_param.plants_per_m2 = 10.0
    mock_param.confidence_threshold = 0.7
    mock_param.created_at = datetime(2025, 10, 20, 14, 30, 0)
    mock_param.updated_at = None

    mock_density_parameter_repo.create.return_value = mock_param
    request = DensityParameterCreateRequest(name="Low Density - Ficus", plants_per_m2=10.0)

    # Act
    result = await density_parameter_service.create(request)

    # Assert
    assert result.density_parameter_id == 2
    assert result.plants_per_m2 == 10.0
    assert result.confidence_threshold == 0.7  # Default value


# ============================================================================
# get_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(
    density_parameter_service, mock_density_parameter_repo, mock_density_parameter
):
    """Test successful retrieval by ID."""
    # Arrange
    mock_density_parameter_repo.get.return_value = mock_density_parameter

    # Act
    result = await density_parameter_service.get_by_id(1)

    # Assert
    assert isinstance(result, DensityParameterResponse)
    assert result.density_parameter_id == 1
    assert result.name == "High Density - Geraniums"
    assert result.plants_per_m2 == 25.5
    assert result.confidence_threshold == 0.8
    mock_density_parameter_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(density_parameter_service, mock_density_parameter_repo):
    """Test ValueError when ID not found."""
    # Arrange
    mock_density_parameter_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await density_parameter_service.get_by_id(999)

    mock_density_parameter_repo.get.assert_called_once_with(999)


# ============================================================================
# get_all tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(
    density_parameter_service, mock_density_parameter_repo, mock_density_parameter
):
    """Test successful retrieval of all density parameters."""
    # Arrange
    mock_param_2 = Mock()
    mock_param_2.density_parameter_id = 2
    mock_param_2.name = "Medium Density - Petunias"
    mock_param_2.plants_per_m2 = 15.0
    mock_param_2.confidence_threshold = 0.75
    mock_param_2.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_param_2.updated_at = None

    mock_density_parameter_repo.get_multi.return_value = [mock_density_parameter, mock_param_2]

    # Act
    result = await density_parameter_service.get_all(limit=100)

    # Assert
    assert len(result) == 2
    assert result[0].density_parameter_id == 1
    assert result[0].name == "High Density - Geraniums"
    assert result[0].plants_per_m2 == 25.5
    assert result[1].density_parameter_id == 2
    assert result[1].name == "Medium Density - Petunias"
    assert result[1].plants_per_m2 == 15.0
    mock_density_parameter_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(density_parameter_service, mock_density_parameter_repo):
    """Test get_all returns empty list when no records exist."""
    # Arrange
    mock_density_parameter_repo.get_multi.return_value = []

    # Act
    result = await density_parameter_service.get_all()

    # Assert
    assert result == []
    mock_density_parameter_repo.get_multi.assert_called_once()


# ============================================================================
# update tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_density_parameter_success(
    density_parameter_service, mock_density_parameter_repo, mock_density_parameter
):
    """Test successful density parameter update."""
    # Arrange
    updated_param = Mock()
    updated_param.density_parameter_id = 1
    updated_param.name = "High Density - Geraniums Updated"
    updated_param.plants_per_m2 = 28.0
    updated_param.confidence_threshold = 0.85
    updated_param.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_param.updated_at = datetime(2025, 10, 20, 16, 0, 0)

    mock_density_parameter_repo.get.return_value = mock_density_parameter
    mock_density_parameter_repo.update.return_value = updated_param

    request = DensityParameterUpdateRequest(
        name="High Density - Geraniums Updated", plants_per_m2=28.0, confidence_threshold=0.85
    )

    # Act
    result = await density_parameter_service.update(1, request)

    # Assert
    assert isinstance(result, DensityParameterResponse)
    assert result.density_parameter_id == 1
    assert result.name == "High Density - Geraniums Updated"
    assert result.plants_per_m2 == 28.0
    assert result.confidence_threshold == 0.85
    mock_density_parameter_repo.get.assert_called_once_with(1)
    mock_density_parameter_repo.update.assert_called_once()
    call_args = mock_density_parameter_repo.update.call_args[0]
    assert call_args[0] == 1
    assert call_args[1]["name"] == "High Density - Geraniums Updated"
    assert call_args[1]["plants_per_m2"] == 28.0
    assert call_args[1]["confidence_threshold"] == 0.85


@pytest.mark.asyncio
async def test_update_density_parameter_not_found(
    density_parameter_service, mock_density_parameter_repo
):
    """Test ValueError when updating non-existent density parameter."""
    # Arrange
    mock_density_parameter_repo.get.return_value = None
    request = DensityParameterUpdateRequest(name="Updated")

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await density_parameter_service.update(999, request)

    mock_density_parameter_repo.get.assert_called_once_with(999)
    mock_density_parameter_repo.update.assert_not_called()


# ============================================================================
# delete tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_density_parameter_success(
    density_parameter_service, mock_density_parameter_repo, mock_density_parameter
):
    """Test successful density parameter deletion."""
    # Arrange
    mock_density_parameter_repo.get.return_value = mock_density_parameter
    mock_density_parameter_repo.delete.return_value = None

    # Act
    result = await density_parameter_service.delete(1)

    # Assert
    assert result is None
    mock_density_parameter_repo.get.assert_called_once_with(1)
    mock_density_parameter_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_density_parameter_not_found(
    density_parameter_service, mock_density_parameter_repo
):
    """Test ValueError when deleting non-existent density parameter."""
    # Arrange
    mock_density_parameter_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await density_parameter_service.delete(999)

    mock_density_parameter_repo.get.assert_called_once_with(999)
    mock_density_parameter_repo.delete.assert_not_called()
