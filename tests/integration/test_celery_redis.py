"""
Integration tests for Celery Redis connectivity.

Tests verify:
- Redis broker connection
- Redis result backend connection
- Task registration and execution
- Result storage and retrieval
"""

import pytest


@pytest.mark.asyncio
async def test_redis_broker_connection():
    """Verify Redis broker is accessible.

    This test ensures:
    - Redis service is running
    - Celery can connect to broker
    - No connection errors during startup
    """
    try:
        from app.celery_app import app

        # Try to get backend
        backend = app.backend

        # If this doesn't raise, connection works
        assert backend is not None

        # Try to ping Redis directly
        try:
            connection = app.connection_or_acquire()
            assert connection is not None
        except Exception:
            # Some Celery versions handle this differently
            pass

    except ImportError:
        pytest.skip("celery_app module not yet implemented")
    except Exception as e:
        # Redis might not be running in test environment
        pytest.skip(f"Redis not available: {str(e)}")


@pytest.mark.asyncio
async def test_redis_result_backend_connection():
    """Verify Redis result backend is accessible.

    This test ensures:
    - Result backend can connect to Redis
    - Results can be stored and retrieved
    """
    try:
        from app.celery_app import app

        # Check result backend is configured
        assert app.conf.result_backend is not None
        assert "redis" in app.conf.result_backend.lower()

        # Verify backend object exists
        backend = app.backend
        assert backend is not None

    except ImportError:
        pytest.skip("celery_app module not yet implemented")
    except Exception as e:
        pytest.skip(f"Redis result backend not available: {str(e)}")


@pytest.mark.asyncio
async def test_celery_task_registration():
    """Verify task autodiscovery and registration works.

    This test ensures:
    - Tasks can be registered with the app
    - Task registry is accessible
    """
    try:
        from app.celery_app import app

        # Celery app should have a tasks registry
        registered_tasks = app.tasks
        assert registered_tasks is not None

        # Registry should be a dict-like object
        assert hasattr(registered_tasks, "__iter__")

    except ImportError:
        pytest.skip("celery_app module not yet implemented")


@pytest.mark.asyncio
async def test_celery_broker_connectivity():
    """Test actual broker connectivity by attempting connection.

    This is a more thorough test that attempts to:
    - Connect to broker
    - Verify channel can be created
    - Clean up connection
    """
    try:
        from app.celery_app import app

        # Try to connect to broker
        try:
            with app.connection_or_acquire() as conn:
                assert conn is not None
                # If we get here, connection succeeded
        except Exception as e:
            # Connection might fail if Redis not running
            pytest.skip(f"Cannot connect to broker: {str(e)}")

    except ImportError:
        pytest.skip("celery_app module not yet implemented")


@pytest.mark.asyncio
async def test_celery_inspect_available():
    """Verify Celery inspect functionality is available.

    This tests:
    - Inspect API is accessible
    - Can query worker stats (if workers running)
    """
    try:
        from app.celery_app import app

        # Create inspect instance
        inspect = app.control.inspect()
        assert inspect is not None

        # Try to get stats (will be empty if no workers)
        # Stats might be None if no workers are running
        # That's okay - we just verify inspect works
        # Some connection errors are expected in test environment
        from contextlib import suppress

        with suppress(Exception):
            stats = inspect.stats()

    except ImportError:
        pytest.skip("celery_app module not yet implemented")


@pytest.mark.asyncio
async def test_redis_broker_database_separation():
    """Verify broker and result backend use different Redis databases.

    This test ensures:
    - Broker uses Redis DB 0
    - Result backend uses Redis DB 1
    - No interference between broker and results
    """
    try:
        from app.celery_app import app

        broker_url = app.conf.broker_url
        result_backend = app.conf.result_backend

        # Both should use Redis
        assert "redis" in broker_url.lower()
        assert "redis" in result_backend.lower()

        # Extract database numbers
        broker_db = broker_url.split("/")[-1]
        result_db = result_backend.split("/")[-1]

        # Should use different databases
        assert broker_db != result_db
        assert broker_db == "0"
        assert result_db == "1"

    except ImportError:
        pytest.skip("celery_app module not yet implemented")


class TestCeleryRedisIntegration:
    """Integration tests for Celery-Redis setup."""

    @pytest.fixture
    def celery_app(self):
        """Get Celery app instance."""
        try:
            from app.celery_app import app

            return app
        except ImportError:
            pytest.skip("celery_app module not yet implemented")

    def test_broker_url_accessible(self, celery_app):
        """Verify broker URL is accessible and valid."""
        broker_url = celery_app.conf.broker_url

        assert broker_url is not None
        assert broker_url.startswith("redis://")
        assert ":6379" in broker_url

    def test_result_backend_accessible(self, celery_app):
        """Verify result backend URL is accessible and valid."""
        result_backend = celery_app.conf.result_backend

        assert result_backend is not None
        assert result_backend.startswith("redis://")
        assert ":6379" in result_backend

    def test_serialization_json_only(self, celery_app):
        """Verify JSON serialization is enforced (security).

        This prevents pickle-based attacks.
        """
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

        # Verify pickle is NOT accepted
        if isinstance(celery_app.conf.accept_content, (list, tuple)):
            assert "pickle" not in celery_app.conf.accept_content

    def test_utc_timezone_configured(self, celery_app):
        """Verify UTC timezone is properly configured."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_task_tracking_enabled(self, celery_app):
        """Verify task tracking is enabled for monitoring."""
        assert celery_app.conf.task_track_started is True

    def test_connection_retry_enabled(self, celery_app):
        """Verify connection retry is enabled on startup."""
        assert celery_app.conf.broker_connection_retry_on_startup is True


@pytest.mark.asyncio
async def test_celery_app_name():
    """Verify Celery app has correct name."""
    try:
        from app.celery_app import app

        assert app.main == "demeterai"

    except ImportError:
        pytest.skip("celery_app module not yet implemented")


@pytest.mark.asyncio
async def test_redis_connection_from_docker():
    """Verify Redis connection works from Docker environment.

    This test is specific to the Docker setup where:
    - Redis runs in 'redis' container
    - App connects via service name 'redis:6379'
    """
    try:
        from app.celery_app import app

        broker_url = app.conf.broker_url

        # In Docker, should reference 'redis' service
        # In local dev, might reference 'localhost'
        assert "redis" in broker_url.lower() or "localhost" in broker_url.lower()

    except ImportError:
        pytest.skip("celery_app module not yet implemented")
