"""Unit tests for BatchLifecycleService.

Tests business logic with NO dependencies (standalone service).
All methods are synchronous business logic calculations.

TESTING STRATEGY:
- No mocks needed (pure business logic)
- Test date calculations
- Test batch status heuristics
- Test edge cases (None values, boundary conditions)

Coverage target: ≥85%

Test categories:
- calculate_batch_age_days: normal, None planting_date
- estimate_ready_date: normal, None planting_date
- check_batch_status: all stages, all health levels

See:
    - Service: app/services/batch_lifecycle_service.py
"""

from datetime import date, timedelta

import pytest

from app.services.batch_lifecycle_service import BatchLifecycleService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def lifecycle_service():
    """Create BatchLifecycleService (no dependencies)."""
    return BatchLifecycleService()


# ============================================================================
# calculate_batch_age_days tests
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_batch_age_days_normal(lifecycle_service):
    """Test batch age calculation with valid planting date."""
    # Arrange
    planting_date = date.today() - timedelta(days=45)

    # Act
    result = await lifecycle_service.calculate_batch_age_days(planting_date)

    # Assert
    assert result == 45


@pytest.mark.asyncio
async def test_calculate_batch_age_days_today(lifecycle_service):
    """Test batch age is 0 for today's planting."""
    # Arrange
    planting_date = date.today()

    # Act
    result = await lifecycle_service.calculate_batch_age_days(planting_date)

    # Assert
    assert result == 0


@pytest.mark.asyncio
async def test_calculate_batch_age_days_none(lifecycle_service):
    """Test batch age returns 0 for None planting_date."""
    # Act
    result = await lifecycle_service.calculate_batch_age_days(None)

    # Assert
    assert result == 0


# ============================================================================
# estimate_ready_date tests
# ============================================================================


@pytest.mark.asyncio
async def test_estimate_ready_date_normal(lifecycle_service):
    """Test ready date estimation with valid growth days."""
    # Arrange
    planting_date = date(2025, 1, 1)
    growth_days = 90

    # Act
    result = await lifecycle_service.estimate_ready_date(planting_date, growth_days)

    # Assert
    expected = date(2025, 4, 1)  # 90 days after Jan 1
    assert result == expected


@pytest.mark.asyncio
async def test_estimate_ready_date_none_planting(lifecycle_service):
    """Test ready date returns today when planting_date is None."""
    # Act
    result = await lifecycle_service.estimate_ready_date(None, 90)

    # Assert
    assert result == date.today()


@pytest.mark.asyncio
async def test_estimate_ready_date_zero_growth(lifecycle_service):
    """Test ready date with zero growth days."""
    # Arrange
    planting_date = date(2025, 1, 1)

    # Act
    result = await lifecycle_service.estimate_ready_date(planting_date, 0)

    # Assert
    assert result == planting_date


# ============================================================================
# check_batch_status tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_batch_status_seedling(lifecycle_service):
    """Test batch status for seedling stage (< 30 days)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=15), "quality_score": 4.5}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["stage"] == "seedling"
    assert result["health"] == "good"
    assert result["age_days"] == 15
    assert result["quality_score"] == 4.5


@pytest.mark.asyncio
async def test_check_batch_status_growing(lifecycle_service):
    """Test batch status for growing stage (30-90 days)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=60), "quality_score": 3.0}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["stage"] == "growing"
    assert result["health"] == "warning"
    assert result["age_days"] == 60


@pytest.mark.asyncio
async def test_check_batch_status_mature(lifecycle_service):
    """Test batch status for mature stage (90-180 days)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=120), "quality_score": 4.2}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["stage"] == "mature"
    assert result["health"] == "good"
    assert result["age_days"] == 120


@pytest.mark.asyncio
async def test_check_batch_status_ready(lifecycle_service):
    """Test batch status for ready stage (>= 180 days)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=200), "quality_score": 2.0}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["stage"] == "ready"
    assert result["health"] == "critical"
    assert result["age_days"] == 200


@pytest.mark.asyncio
async def test_check_batch_status_default_quality(lifecycle_service):
    """Test batch status uses default quality_score (3.0)."""
    # Arrange
    batch_data = {
        "planting_date": date.today() - timedelta(days=50),
        # quality_score not provided
    }

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["quality_score"] == 3.0
    assert result["health"] == "warning"


@pytest.mark.asyncio
async def test_check_batch_status_boundary_stage_30_days(lifecycle_service):
    """Test stage boundary at exactly 30 days (should be growing)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=30), "quality_score": 4.0}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["stage"] == "growing"  # 30 days is NOT < 30


@pytest.mark.asyncio
async def test_check_batch_status_boundary_stage_90_days(lifecycle_service):
    """Test stage boundary at exactly 90 days (should be mature)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=90), "quality_score": 4.0}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["stage"] == "mature"  # 90 days is NOT < 90


@pytest.mark.asyncio
async def test_check_batch_status_boundary_health_good(lifecycle_service):
    """Test health boundary at exactly 4.0 (should be good)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=45), "quality_score": 4.0}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["health"] == "good"  # 4.0 >= 4.0


@pytest.mark.asyncio
async def test_check_batch_status_boundary_health_warning(lifecycle_service):
    """Test health boundary at exactly 2.5 (should be warning)."""
    # Arrange
    batch_data = {"planting_date": date.today() - timedelta(days=45), "quality_score": 2.5}

    # Act
    result = await lifecycle_service.check_batch_status(batch_data)

    # Assert
    assert result["health"] == "warning"  # 2.5 >= 2.5
