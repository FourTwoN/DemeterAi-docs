"""Integration tests for OpenTelemetry SDK and trace export functionality.

Tests cover:
- OTEL SDK initialization
- Trace export functionality
- OTLP endpoint connectivity (graceful handling if down)
- Tracer and meter creation
- Auto-instrumentation verification
- Resource attributes configuration

Coverage Target: >= 80% for app.core.telemetry
"""

from unittest.mock import MagicMock, patch

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider

from app.core.config import settings
from app.core.telemetry import (
    _create_resource,
    _instrument_libraries,
    _setup_metrics_provider,
    _setup_trace_provider,
    get_meter,
    get_tracer,
    setup_telemetry,
)


class TestTelemetryInitialization:
    """Test OTEL SDK initialization and configuration."""

    def test_create_resource_contains_service_attributes(self):
        """Test that resource includes all required service attributes."""
        # Act
        resource = _create_resource()

        # Assert
        assert resource.attributes is not None
        assert resource.attributes.get("service.name") == settings.OTEL_SERVICE_NAME
        assert resource.attributes.get("service.version") == "2.0.0"
        assert resource.attributes.get("deployment.environment") == settings.APP_ENV
        assert resource.attributes.get("service.namespace") == "demeterai"

    def test_create_resource_uses_settings_values(self):
        """Test that resource uses values from settings."""
        # Arrange
        resource = _create_resource()

        # Assert
        assert resource.attributes.get("service.name") == settings.OTEL_SERVICE_NAME
        assert resource.attributes.get("deployment.environment") == settings.APP_ENV

    @patch("app.core.telemetry.settings.OTEL_ENABLED", False)
    def test_setup_telemetry_disabled_returns_none(self):
        """Test that setup_telemetry returns None when disabled."""
        # Act
        result = setup_telemetry()

        # Assert
        assert result is None

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_setup_telemetry_enabled_returns_providers(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that setup_telemetry returns providers when enabled."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.return_value = MagicMock()

        # Act
        result = setup_telemetry()

        # Assert
        assert result is not None
        tracer_provider, metric_reader, meter_provider = result
        assert isinstance(tracer_provider, TracerProvider)
        assert isinstance(metric_reader, PeriodicExportingMetricReader)
        assert isinstance(meter_provider, MeterProvider)
        mock_instrument.assert_called_once()


class TestTraceProvider:
    """Test trace provider configuration and span export."""

    @patch("app.core.telemetry.OTLPSpanExporter")
    def test_setup_trace_provider_creates_tracer_provider(self, mock_exporter):
        """Test that trace provider is created and configured correctly."""
        # Arrange
        mock_exporter.return_value = MagicMock()
        resource = _create_resource()

        # Act
        tracer_provider = _setup_trace_provider(resource)

        # Assert
        assert isinstance(tracer_provider, TracerProvider)
        assert tracer_provider.resource == resource

        # Verify OTLP exporter was configured
        mock_exporter.assert_called_once()
        call_kwargs = mock_exporter.call_args.kwargs
        assert call_kwargs["endpoint"] == settings.OTEL_EXPORTER_OTLP_ENDPOINT
        assert call_kwargs["insecure"] is True

    @patch("app.core.telemetry.OTLPSpanExporter")
    def test_setup_trace_provider_registers_globally(self, mock_exporter):
        """Test that trace provider is registered globally."""
        # Arrange
        mock_exporter.return_value = MagicMock()
        resource = _create_resource()

        # Act
        tracer_provider = _setup_trace_provider(resource)

        # Assert
        # Global tracer provider should be set
        global_provider = trace.get_tracer_provider()
        assert global_provider == tracer_provider

    @patch("app.core.telemetry.OTLPSpanExporter")
    def test_setup_trace_provider_configures_batch_processor(self, mock_exporter):
        """Test that batch span processor is configured correctly."""
        # Arrange
        mock_exporter.return_value = MagicMock()
        resource = _create_resource()

        # Act
        tracer_provider = _setup_trace_provider(resource)

        # Assert
        # Verify span processor was added
        assert len(tracer_provider._active_span_processor._span_processors) > 0


class TestMetricsProvider:
    """Test metrics provider configuration and collection."""

    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_setup_metrics_provider_creates_meter_provider(self, mock_exporter):
        """Test that metrics provider is created and configured correctly."""
        # Arrange
        mock_exporter.return_value = MagicMock()
        resource = _create_resource()

        # Act
        metric_reader, meter_provider = _setup_metrics_provider(resource)

        # Assert
        assert isinstance(metric_reader, PeriodicExportingMetricReader)
        assert isinstance(meter_provider, MeterProvider)
        assert meter_provider._sdk_config.resource == resource

        # Verify OTLP exporter was configured
        mock_exporter.assert_called_once()
        call_kwargs = mock_exporter.call_args.kwargs
        assert call_kwargs["endpoint"] == settings.OTEL_EXPORTER_OTLP_ENDPOINT
        assert call_kwargs["insecure"] is True

    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_setup_metrics_provider_configures_periodic_export(self, mock_exporter):
        """Test that periodic metric export is configured correctly."""
        # Arrange
        mock_exporter.return_value = MagicMock()
        resource = _create_resource()

        # Act
        metric_reader, meter_provider = _setup_metrics_provider(resource)

        # Assert
        # Verify export interval (60 seconds = 60000 milliseconds)
        assert metric_reader._export_interval_millis == 60000

    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_setup_metrics_provider_registers_globally(self, mock_exporter):
        """Test that metrics provider is registered globally."""
        # Arrange
        mock_exporter.return_value = MagicMock()
        resource = _create_resource()

        # Act
        metric_reader, meter_provider = _setup_metrics_provider(resource)

        # Assert
        # Global meter provider should be set
        global_provider = metrics.get_meter_provider()
        assert global_provider == meter_provider


class TestAutoInstrumentation:
    """Test automatic instrumentation of libraries."""

    @patch("app.core.telemetry.FastAPIInstrumentor")
    @patch("app.core.telemetry.SQLAlchemyInstrumentor")
    @patch("app.core.telemetry.CeleryInstrumentor")
    @patch("app.core.telemetry.RedisInstrumentor")
    @patch("app.core.telemetry.RequestsInstrumentor")
    def test_instrument_libraries_enables_all_instrumentors(
        self,
        mock_requests,
        mock_redis,
        mock_celery,
        mock_sqlalchemy,
        mock_fastapi,
    ):
        """Test that all auto-instrumentations are enabled."""
        # Arrange
        mock_fastapi.return_value.instrument = MagicMock()
        mock_sqlalchemy.return_value.instrument = MagicMock()
        mock_celery.return_value.instrument = MagicMock()
        mock_redis.return_value.instrument = MagicMock()
        mock_requests.return_value.instrument = MagicMock()

        # Act
        _instrument_libraries()

        # Assert
        mock_fastapi.return_value.instrument.assert_called_once()
        mock_sqlalchemy.return_value.instrument.assert_called_once()
        mock_celery.return_value.instrument.assert_called_once()
        mock_redis.return_value.instrument.assert_called_once()
        mock_requests.return_value.instrument.assert_called_once()


class TestTracerAndMeterCreation:
    """Test tracer and meter creation for custom spans and metrics."""

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_get_tracer_returns_tracer_instance(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that get_tracer returns a valid tracer instance."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.return_value = MagicMock()
        setup_telemetry()

        # Act
        tracer = get_tracer(__name__)

        # Assert
        assert tracer is not None
        assert hasattr(tracer, "start_span")
        assert hasattr(tracer, "start_as_current_span")

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_get_meter_returns_meter_instance(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that get_meter returns a valid meter instance."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.return_value = MagicMock()
        setup_telemetry()

        # Act
        meter = get_meter(__name__)

        # Assert
        assert meter is not None
        assert hasattr(meter, "create_counter")
        assert hasattr(meter, "create_histogram")
        assert hasattr(meter, "create_gauge")


class TestOTLPEndpointConnectivity:
    """Test graceful handling when OTLP endpoint is unavailable."""

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_setup_telemetry_handles_exporter_initialization_failure(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that setup fails gracefully if OTLP exporter initialization fails."""
        # Arrange
        mock_span_exporter.side_effect = Exception("Connection refused")

        # Act
        result = setup_telemetry()

        # Assert
        # Should return None on failure (graceful degradation)
        assert result is None

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_setup_telemetry_handles_metric_exporter_failure(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that setup fails gracefully if metric exporter initialization fails."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.side_effect = Exception("OTLP endpoint unreachable")

        # Act
        result = setup_telemetry()

        # Assert
        # Should return None on failure (graceful degradation)
        assert result is None


class TestSpanCreation:
    """Test custom span creation and context propagation."""

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_tracer_creates_spans_with_context(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that tracer can create spans with proper context."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.return_value = MagicMock()
        setup_telemetry()
        tracer = get_tracer(__name__)

        # Act
        with tracer.start_as_current_span("test_span") as span:
            # Assert
            assert span is not None
            assert span.is_recording()
            assert span.get_span_context().trace_id > 0
            assert span.get_span_context().span_id > 0

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_nested_spans_maintain_trace_context(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that nested spans maintain trace context (parent-child relationship)."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.return_value = MagicMock()
        setup_telemetry()
        tracer = get_tracer(__name__)

        # Act
        with tracer.start_as_current_span("parent_span") as parent:
            parent_trace_id = parent.get_span_context().trace_id
            parent_span_id = parent.get_span_context().span_id

            with tracer.start_as_current_span("child_span") as child:
                child_trace_id = child.get_span_context().trace_id
                child_span_id = child.get_span_context().span_id

                # Assert
                # Child span should have same trace_id as parent
                assert child_trace_id == parent_trace_id
                # Child span should have different span_id
                assert child_span_id != parent_span_id


class TestMetricCollection:
    """Test custom metric collection and recording."""

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_meter_creates_counter_metric(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that meter can create counter metrics."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.return_value = MagicMock()
        setup_telemetry()
        meter = get_meter(__name__)

        # Act
        counter = meter.create_counter(
            name="test_counter",
            description="Test counter metric",
            unit="1",
        )

        # Assert
        assert counter is not None
        # Should be able to add values
        counter.add(1, {"label": "test"})
        counter.add(5, {"label": "test"})

    @patch("app.core.telemetry.settings.OTEL_ENABLED", True)
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    def test_meter_creates_histogram_metric(
        self,
        mock_metric_exporter,
        mock_span_exporter,
        mock_instrument,
    ):
        """Test that meter can create histogram metrics."""
        # Arrange
        mock_span_exporter.return_value = MagicMock()
        mock_metric_exporter.return_value = MagicMock()
        setup_telemetry()
        meter = get_meter(__name__)

        # Act
        histogram = meter.create_histogram(
            name="test_histogram",
            description="Test histogram metric",
            unit="ms",
        )

        # Assert
        assert histogram is not None
        # Should be able to record values
        histogram.record(42.5, {"label": "test"})
        histogram.record(123.7, {"label": "test"})
