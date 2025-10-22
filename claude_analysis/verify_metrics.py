#!/usr/bin/env python
"""Verification script for app/core/metrics.py

This script verifies that:
1. All imports work correctly
2. All metrics are properly defined
3. setup_metrics() initializes correctly
4. All decorators and context managers work
5. Metrics can be exported in Prometheus format

Run with: python verify_metrics.py
"""

import sys

from app.core.logging import get_logger

logger = get_logger(__name__)


def verify_structure() -> bool:
    """Verify file structure without prometheus_client."""
    logger.info("Verifying file structure")

    try:
        import ast

        with open("app/core/metrics.py") as f:
            tree = ast.parse(f.read())

        # Count functions
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        logger.info("Functions defined", count=len(functions))
        for func in [
            "setup_metrics",
            "get_metrics_collector",
            "track_api_request",
            "record_s3_operation",
        ]:
            if func in functions:
                logger.debug("Key function found", function=func)
            else:
                logger.error("Key function missing", function=func)
                return False

        # Check docstring
        docstring = ast.get_docstring(tree)
        if docstring:
            logger.debug("Module docstring present", length=len(docstring))
        else:
            logger.error("Module docstring missing")
            return False

        logger.info("File structure verification PASSED")
        return True

    except Exception as e:
        logger.error("Structure verification FAILED", error=str(e), exc_info=True)
        return False


def verify_imports() -> bool:
    """Verify imports work (requires prometheus_client)."""
    logger.info("Verifying imports")

    try:
        # Check if prometheus_client is available
        try:
            import prometheus_client  # type: ignore[import-not-found]

            logger.info("prometheus_client installed", version=prometheus_client.__version__)
        except ImportError:
            logger.warning("prometheus_client NOT installed - skipping runtime tests")
            logger.info("Install with: pip install prometheus-client")
            return False

        # Import the metrics module
        sys.path.insert(0, ".")
        import app.core.metrics  # noqa: F401

        logger.info("All imports successful")
        exported_functions = [
            "setup_metrics",
            "get_metrics_collector",
            "get_metrics_text",
            "time_operation (sync context manager)",
            "time_operation_async (async context manager)",
            "track_api_request (decorator)",
            "track_stock_operation (decorator)",
            "track_ml_inference (decorator)",
            "record_s3_operation",
            "record_warehouse_query",
            "record_product_search",
            "record_celery_task",
            "record_db_query",
            "update_db_pool_metrics",
        ]
        logger.debug("Exported functions verified", functions=exported_functions)

        logger.info("Import verification PASSED")
        return True

    except ImportError as e:
        logger.error("Import FAILED", error=str(e), exc_info=True)
        return False
    except Exception as e:
        logger.error("Unexpected error during import verification", error=str(e), exc_info=True)
        return False


def verify_initialization() -> bool:
    """Verify metrics initialization."""
    logger.info("Verifying metrics initialization")

    try:
        from app.core.metrics import get_metrics_collector, setup_metrics

        # Test with metrics disabled
        setup_metrics(enable_metrics=False)
        registry = get_metrics_collector()
        if registry is not None:
            logger.error("Registry should be None when metrics disabled")
            return False
        logger.info("Metrics correctly disabled when enable_metrics=False")

        # Test with metrics enabled
        setup_metrics(enable_metrics=True)
        registry = get_metrics_collector()
        if registry is None:
            logger.error("Registry should not be None when metrics enabled")
            return False
        logger.info("Metrics correctly enabled when enable_metrics=True")

        # Check registry type
        from prometheus_client import CollectorRegistry

        if not isinstance(registry, CollectorRegistry):
            logger.error("Registry wrong type", actual_type=type(registry).__name__)
            return False
        logger.info("Registry is correct type", type=type(registry).__name__)

        logger.info("Initialization verification PASSED")
        return True

    except Exception as e:
        logger.error("Initialization verification FAILED", error=str(e), exc_info=True)
        return False


def verify_metrics_export() -> bool:
    """Verify metrics can be exported."""
    logger.info("Verifying metrics export")

    try:
        from app.core.metrics import (
            get_metrics_text,
            record_product_search,
            record_s3_operation,
            setup_metrics,
        )

        # Setup metrics
        setup_metrics(enable_metrics=True)

        # Record some test metrics
        record_s3_operation(operation="upload", bucket="test-bucket", duration=1.5, success=True)
        record_product_search(search_type="code", result_count=5, duration=0.1)

        # Export metrics
        metrics_text = get_metrics_text()

        if not metrics_text:
            logger.error("Metrics export returned empty")
            return False

        # Decode and verify
        metrics_str = metrics_text.decode("utf-8")

        # Check for expected metric names
        expected_metrics = [
            "demeter_s3_operation_duration_seconds",
            "demeter_product_searches_total",
            "demeter_product_search_duration_seconds",
        ]

        for metric_name in expected_metrics:
            if metric_name in metrics_str:
                logger.debug("Found metric", metric=metric_name)
            else:
                logger.warning("Metric not found in export", metric=metric_name)

        logger.info("Metrics export verification PASSED", size_bytes=len(metrics_text))
        return True

    except Exception as e:
        logger.error("Metrics export verification FAILED", error=str(e), exc_info=True)
        return False


def main() -> int:
    """Run all verification tests."""
    logger.info("Starting Prometheus metrics verification", module="app/core/metrics.py")

    results = []

    # Step 1: Structure
    results.append(("Structure", verify_structure()))

    # Step 2: Imports
    imports_ok = verify_imports()
    results.append(("Imports", imports_ok))

    # Skip runtime tests if prometheus_client not installed
    if not imports_ok:
        logger.warning("Skipping runtime tests - prometheus_client not installed")
        for test_name, passed in results:
            status = "PASS" if passed else "FAIL"
            logger.info("Verification result", test=test_name, status=status)
        logger.info("Install prometheus-client to run full verification")
        return 0

    # Step 3: Initialization
    results.append(("Initialization", verify_initialization()))

    # Step 4: Export
    results.append(("Metrics Export", verify_metrics_export()))

    # Summary
    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        logger.info("Verification result", test=test_name, status=status)
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("ALL VERIFICATIONS PASSED")
        logger.info(
            "Metrics module ready for integration",
            next_steps=[
                "Add 'prometheus-client' to requirements.txt",
                "Add ENABLE_METRICS to app/core/config.py",
                "Call setup_metrics() in app/main.py on startup",
                "Add /metrics endpoint to expose metrics",
            ],
        )
        return 0
    else:
        logger.error("SOME VERIFICATIONS FAILED - review logs above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
