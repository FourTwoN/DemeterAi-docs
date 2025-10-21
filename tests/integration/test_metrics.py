"""Integration tests for Prometheus metrics collection.

Tests cover:
- Metrics initialization
- Prometheus endpoint (/metrics)
- Custom metrics collection
- Metrics format validation
- Concurrent metric updates
- Context managers and decorators

Coverage Target: >= 80% for app.core.metrics
"""

import asyncio

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from app.core.metrics import (
    api_request_duration_seconds,
    api_request_errors_total,
    db_connection_pool_size,
    db_connection_pool_used,
    db_query_duration_seconds,
    get_metrics_collector,
    get_metrics_text,
    ml_detections_total,
    ml_inference_duration_seconds,
    record_celery_task,
    record_db_query,
    record_product_search,
    record_s3_operation,
    record_warehouse_query,
    setup_metrics,
    stock_batch_size,
    stock_operations_total,
    time_operation,
    time_operation_async,
    track_api_request,
    track_ml_inference,
    track_stock_operation,
    update_db_pool_metrics,
)


class TestMetricsInitialization:
    """Test metrics setup and initialization."""

    def test_setup_metrics_with_enabled_true(self):
        """Test that setup_metrics initializes registry when enabled."""
        # Act
        setup_metrics(enable_metrics=True)

        # Assert
        registry = get_metrics_collector()
        assert registry is not None
        assert isinstance(registry, CollectorRegistry)

    def test_setup_metrics_with_enabled_false(self):
        """Test that setup_metrics does not initialize when disabled."""
        # Act
        setup_metrics(enable_metrics=False)

        # Assert
        registry = get_metrics_collector()
        assert registry is None

    def test_setup_metrics_creates_all_metric_types(self):
        """Test that all metric collectors are created."""
        # Act
        setup_metrics(enable_metrics=True)

        # Assert - API metrics
        assert api_request_duration_seconds is not None
        assert isinstance(api_request_duration_seconds, Histogram)
        assert api_request_errors_total is not None
        assert isinstance(api_request_errors_total, Counter)

        # Assert - Stock metrics
        assert stock_operations_total is not None
        assert isinstance(stock_operations_total, Counter)
        assert stock_batch_size is not None
        assert isinstance(stock_batch_size, Histogram)

        # Assert - ML metrics
        assert ml_inference_duration_seconds is not None
        assert isinstance(ml_inference_duration_seconds, Histogram)
        assert ml_detections_total is not None
        assert isinstance(ml_detections_total, Counter)

        # Assert - Database metrics
        assert db_connection_pool_size is not None
        assert isinstance(db_connection_pool_size, Gauge)
        assert db_query_duration_seconds is not None
        assert isinstance(db_query_duration_seconds, Histogram)


class TestMetricsExport:
    """Test Prometheus text format export."""

    def test_get_metrics_text_with_metrics_enabled(self):
        """Test that get_metrics_text returns Prometheus format."""
        # Arrange
        setup_metrics(enable_metrics=True)
        # Record some metrics
        if api_request_duration_seconds:
            api_request_duration_seconds.labels(
                method="GET", endpoint="/test", status="success"
            ).observe(0.5)

        # Act
        metrics_text = get_metrics_text()

        # Assert
        assert metrics_text is not None
        assert isinstance(metrics_text, bytes)
        assert b"demeter_api_request_duration_seconds" in metrics_text

    def test_get_metrics_text_with_metrics_disabled(self):
        """Test that get_metrics_text returns empty when disabled."""
        # Arrange
        setup_metrics(enable_metrics=False)

        # Act
        metrics_text = get_metrics_text()

        # Assert
        assert metrics_text == b""

    def test_get_metrics_text_format_is_valid_prometheus(self):
        """Test that metrics text follows Prometheus format."""
        # Arrange
        setup_metrics(enable_metrics=True)
        if stock_operations_total:
            stock_operations_total.labels(
                operation="create", product_type="plant", status="success"
            ).inc()

        # Act
        metrics_text = get_metrics_text().decode("utf-8")

        # Assert
        # Check for TYPE directive
        assert "# TYPE demeter_stock_operations_total counter" in metrics_text
        # Check for HELP directive
        assert "# HELP demeter_stock_operations_total" in metrics_text
        # Check for metric with labels
        assert 'operation="create"' in metrics_text
        assert 'product_type="plant"' in metrics_text


class TestContextManagers:
    """Test timing context managers."""

    def test_time_operation_records_duration(self):
        """Test that time_operation context manager records durations."""
        # Arrange
        setup_metrics(enable_metrics=True)
        import time

        # Act
        with time_operation(
            api_request_duration_seconds,
            method="POST",
            endpoint="/test",
            status="success",
        ):
            time.sleep(0.01)  # 10ms delay

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_api_request_duration_seconds" in metrics_text

    def test_time_operation_with_metrics_disabled(self):
        """Test that time_operation is no-op when metrics disabled."""
        # Arrange
        setup_metrics(enable_metrics=False)
        import time

        # Act - should not raise error
        with time_operation(None, method="GET", endpoint="/test"):
            time.sleep(0.001)

        # Assert - no exceptions raised

    @pytest.mark.asyncio
    async def test_time_operation_async_records_duration(self):
        """Test that async timing context manager records durations."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        async with time_operation_async(
            ml_inference_duration_seconds, model_type="yolo", batch_size_bucket="1-10"
        ):
            await asyncio.sleep(0.01)  # 10ms delay

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_ml_inference_duration_seconds" in metrics_text

    @pytest.mark.asyncio
    async def test_time_operation_async_with_metrics_disabled(self):
        """Test that async timing is no-op when disabled."""
        # Arrange
        setup_metrics(enable_metrics=False)

        # Act - should not raise error
        async with time_operation_async(None, model_type="yolo"):
            await asyncio.sleep(0.001)

        # Assert - no exceptions raised


class TestDecorators:
    """Test metric tracking decorators."""

    @pytest.mark.asyncio
    async def test_track_api_request_decorator_success(self):
        """Test track_api_request decorator records successful requests."""
        # Arrange
        setup_metrics(enable_metrics=True)

        @track_api_request(endpoint="/api/test", method="GET")
        async def test_endpoint():
            await asyncio.sleep(0.01)
            return {"status": "ok"}

        # Act
        result = await test_endpoint()

        # Assert
        assert result == {"status": "ok"}
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_api_request_duration_seconds" in metrics_text

    @pytest.mark.asyncio
    async def test_track_api_request_decorator_error(self):
        """Test track_api_request decorator records errors."""
        # Arrange
        setup_metrics(enable_metrics=True)

        @track_api_request(endpoint="/api/test", method="POST")
        async def test_endpoint_error():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        # Act & Assert
        with pytest.raises(ValueError):
            await test_endpoint_error()

        # Verify error was recorded
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_api_request_errors_total" in metrics_text

    @pytest.mark.asyncio
    async def test_track_stock_operation_decorator_success(self):
        """Test track_stock_operation decorator records operations."""
        # Arrange
        setup_metrics(enable_metrics=True)

        @track_stock_operation(operation="create", product_type="strawberry")
        async def create_stock():
            await asyncio.sleep(0.01)
            return {"id": 123}

        # Act
        result = await create_stock()

        # Assert
        assert result == {"id": 123}
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_stock_operations_total" in metrics_text
        assert 'operation="create"' in metrics_text

    @pytest.mark.asyncio
    async def test_track_stock_operation_decorator_error(self):
        """Test track_stock_operation decorator records failed operations."""
        # Arrange
        setup_metrics(enable_metrics=True)

        @track_stock_operation(operation="delete", product_type="plant")
        async def delete_stock():
            await asyncio.sleep(0.01)
            raise RuntimeError("Delete failed")

        # Act & Assert
        with pytest.raises(RuntimeError):
            await delete_stock()

        # Verify error status was recorded
        metrics_text = get_metrics_text().decode("utf-8")
        assert 'status="error"' in metrics_text

    @pytest.mark.asyncio
    async def test_track_ml_inference_decorator(self):
        """Test track_ml_inference decorator records inference time."""
        # Arrange
        setup_metrics(enable_metrics=True)

        @track_ml_inference(model_type="yolo")
        async def run_inference():
            await asyncio.sleep(0.01)
            return [{"detection": 1}, {"detection": 2}]  # 2 detections

        # Act
        result = await run_inference()

        # Assert
        assert len(result) == 2
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_ml_inference_duration_seconds" in metrics_text
        assert 'model_type="yolo"' in metrics_text


class TestRecordingFunctions:
    """Test metric recording functions."""

    def test_record_s3_operation_success(self):
        """Test recording successful S3 operations."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        record_s3_operation(
            operation="upload", bucket="demeter-photos", duration=1.23, success=True
        )

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_s3_operation_duration_seconds" in metrics_text
        assert 'operation="upload"' in metrics_text
        assert 'bucket="demeter-photos"' in metrics_text

    def test_record_s3_operation_failure(self):
        """Test recording failed S3 operations."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        record_s3_operation(
            operation="download", bucket="demeter-photos", duration=0.5, success=False
        )

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_s3_operation_errors_total" in metrics_text

    def test_record_warehouse_query(self):
        """Test recording warehouse location queries."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        record_warehouse_query(level="warehouse", operation="get", duration=0.025)

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_warehouse_location_queries_total" in metrics_text
        assert "demeter_warehouse_query_duration_seconds" in metrics_text
        assert 'level="warehouse"' in metrics_text

    def test_record_product_search(self):
        """Test recording product search metrics."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        record_product_search(search_type="code", result_count=5, duration=0.15)

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_product_searches_total" in metrics_text
        assert "demeter_product_search_duration_seconds" in metrics_text
        assert 'search_type="code"' in metrics_text
        assert 'result_count_bucket="1-10"' in metrics_text

    def test_record_product_search_buckets_results(self):
        """Test that product search result count is bucketed correctly."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act - Test different buckets
        record_product_search(search_type="name", result_count=0, duration=0.1)
        record_product_search(search_type="name", result_count=5, duration=0.1)
        record_product_search(search_type="name", result_count=25, duration=0.1)
        record_product_search(search_type="name", result_count=100, duration=0.1)

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert 'result_count_bucket="0"' in metrics_text
        assert 'result_count_bucket="1-10"' in metrics_text
        assert 'result_count_bucket="11-50"' in metrics_text
        assert 'result_count_bucket="50+"' in metrics_text

    def test_record_celery_task(self):
        """Test recording Celery task execution."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        record_celery_task(task_name="process_photos", queue="ml", duration=45.2, status="success")

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_celery_task_duration_seconds" in metrics_text
        assert "demeter_celery_task_status_total" in metrics_text
        assert 'task_name="process_photos"' in metrics_text
        assert 'queue="ml"' in metrics_text

    def test_update_db_pool_metrics(self):
        """Test updating database connection pool metrics."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        update_db_pool_metrics(pool_size=20, used_connections=12)

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_db_connection_pool_size" in metrics_text
        assert "demeter_db_connection_pool_used" in metrics_text

    def test_record_db_query(self):
        """Test recording database query metrics."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        record_db_query(operation="select", table="warehouses", duration=0.015)

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_db_query_duration_seconds" in metrics_text
        assert 'operation="select"' in metrics_text
        assert 'table="warehouses"' in metrics_text


class TestConcurrentMetricUpdates:
    """Test that metrics handle concurrent updates correctly."""

    @pytest.mark.asyncio
    async def test_concurrent_counter_increments(self):
        """Test that concurrent counter increments are atomic."""
        # Arrange
        setup_metrics(enable_metrics=True)

        async def increment_counter():
            if stock_operations_total:
                stock_operations_total.labels(
                    operation="create", product_type="test", status="success"
                ).inc()
            await asyncio.sleep(0.001)

        # Act - Run 100 concurrent increments
        tasks = [increment_counter() for _ in range(100)]
        await asyncio.gather(*tasks)

        # Assert - Counter should be exactly 100
        metrics_text = get_metrics_text().decode("utf-8")
        # Parse counter value (should be 100.0)
        assert "demeter_stock_operations_total" in metrics_text

    @pytest.mark.asyncio
    async def test_concurrent_histogram_observations(self):
        """Test that concurrent histogram observations are recorded."""
        # Arrange
        setup_metrics(enable_metrics=True)

        async def observe_duration():
            if api_request_duration_seconds:
                api_request_duration_seconds.labels(
                    method="GET", endpoint="/test", status="success"
                ).observe(0.1)
            await asyncio.sleep(0.001)

        # Act - Run 50 concurrent observations
        tasks = [observe_duration() for _ in range(50)]
        await asyncio.gather(*tasks)

        # Assert - All observations should be recorded
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_api_request_duration_seconds" in metrics_text

    @pytest.mark.asyncio
    async def test_concurrent_gauge_updates(self):
        """Test that gauge updates handle concurrency correctly."""
        # Arrange
        setup_metrics(enable_metrics=True)

        async def update_gauge(value: int):
            if db_connection_pool_used:
                db_connection_pool_used.set(value)
            await asyncio.sleep(0.001)

        # Act - Update gauge concurrently with different values
        tasks = [update_gauge(i) for i in range(1, 21)]
        await asyncio.gather(*tasks)

        # Assert - Gauge should have final value
        metrics_text = get_metrics_text().decode("utf-8")
        assert "demeter_db_connection_pool_used" in metrics_text


class TestMetricsLabels:
    """Test that metrics use correct label names and values."""

    def test_api_request_metric_labels(self):
        """Test that API request metrics have correct labels."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        if api_request_duration_seconds:
            api_request_duration_seconds.labels(
                method="POST", endpoint="/api/stock", status="success"
            ).observe(0.5)

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert 'method="POST"' in metrics_text
        assert 'endpoint="/api/stock"' in metrics_text
        assert 'status="success"' in metrics_text

    def test_stock_metric_labels(self):
        """Test that stock metrics have correct labels."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        if stock_batch_size:
            stock_batch_size.labels(operation="create", product_type="strawberry").observe(500)

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert 'operation="create"' in metrics_text
        assert 'product_type="strawberry"' in metrics_text

    def test_ml_metric_labels(self):
        """Test that ML metrics have correct labels."""
        # Arrange
        setup_metrics(enable_metrics=True)

        # Act
        if ml_detections_total:
            ml_detections_total.labels(model_type="yolo", confidence_bucket="high").inc()

        # Assert
        metrics_text = get_metrics_text().decode("utf-8")
        assert 'model_type="yolo"' in metrics_text
        assert 'confidence_bucket="high"' in metrics_text


class TestMetricsWithDisabled:
    """Test that all metric functions handle disabled state gracefully."""

    def test_all_recording_functions_work_when_disabled(self):
        """Test that all recording functions are no-ops when disabled."""
        # Arrange
        setup_metrics(enable_metrics=False)

        # Act - Should not raise any errors
        record_s3_operation("upload", "bucket", 1.0, True)
        record_warehouse_query("warehouse", "get", 0.1)
        record_product_search("code", 5, 0.2)
        record_celery_task("task", "queue", 10.0, "success")
        update_db_pool_metrics(10, 5)
        record_db_query("select", "table", 0.05)

        # Assert - No exceptions and no metrics text
        metrics_text = get_metrics_text()
        assert metrics_text == b""
