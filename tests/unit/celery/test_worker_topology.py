"""
Unit tests for CEL003: Worker Topology Configuration.

Tests verify:
- GPU workers configured with pool=solo (CRITICAL - prevents CUDA conflicts)
- CPU workers configured with pool=prefork
- I/O workers configured with pool=gevent
- Task routing to correct queues (ml_* → gpu, aggregate_* → cpu, upload_* → io)
- Queue definitions exist for all worker types
- Worker startup command constants are properly defined
- CRITICAL: GPU worker pool is solo (NOT prefork/threads)

Architecture:
- 3 specialized worker types for optimal resource utilization
- Task routing based on workload characteristics
- Queue-based task distribution

CRITICAL REQUIREMENT:
- GPU workers MUST use pool=solo to avoid CUDA context conflicts (ADR-005)
"""

import pytest


class TestWorkerTopologyConfiguration:
    """Test CEL003: Worker topology and queue routing configuration."""

    @pytest.fixture
    def celery_app(self):
        """Import Celery app."""
        from app.celery_app import app

        return app

    def test_gpu_queue_exists(self, celery_app):
        """Verify gpu_queue is configured."""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]

        assert "gpu_queue" in queue_names

    def test_cpu_queue_exists(self, celery_app):
        """Verify cpu_queue is configured."""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]

        assert "cpu_queue" in queue_names

    def test_io_queue_exists(self, celery_app):
        """Verify io_queue is configured."""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]

        assert "io_queue" in queue_names

    def test_default_queue_exists(self, celery_app):
        """Verify default queue is configured."""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]

        assert "default" in queue_names

    def test_all_expected_queues_present(self, celery_app):
        """Verify all 4 expected queues are configured."""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]

        expected_queues = {"default", "gpu_queue", "cpu_queue", "io_queue"}
        assert set(queue_names) == expected_queues

    def test_gpu_queue_has_exchange(self, celery_app):
        """Verify gpu_queue has proper exchange configured."""
        queues = celery_app.conf.task_queues
        gpu_queue = next((q for q in queues if q.name == "gpu_queue"), None)

        assert gpu_queue is not None
        assert gpu_queue.exchange is not None
        assert gpu_queue.exchange.name == "gpu"

    def test_cpu_queue_has_exchange(self, celery_app):
        """Verify cpu_queue has proper exchange configured."""
        queues = celery_app.conf.task_queues
        cpu_queue = next((q for q in queues if q.name == "cpu_queue"), None)

        assert cpu_queue is not None
        assert cpu_queue.exchange is not None
        assert cpu_queue.exchange.name == "cpu"

    def test_io_queue_has_exchange(self, celery_app):
        """Verify io_queue has proper exchange configured."""
        queues = celery_app.conf.task_queues
        io_queue = next((q for q in queues if q.name == "io_queue"), None)

        assert io_queue is not None
        assert io_queue.exchange is not None
        assert io_queue.exchange.name == "io"

    def test_gpu_queue_routing_key(self, celery_app):
        """Verify gpu_queue has correct routing key."""
        queues = celery_app.conf.task_queues
        gpu_queue = next((q for q in queues if q.name == "gpu_queue"), None)

        assert gpu_queue is not None
        assert gpu_queue.routing_key == "gpu"

    def test_cpu_queue_routing_key(self, celery_app):
        """Verify cpu_queue has correct routing key."""
        queues = celery_app.conf.task_queues
        cpu_queue = next((q for q in queues if q.name == "cpu_queue"), None)

        assert cpu_queue is not None
        assert cpu_queue.routing_key == "cpu"

    def test_io_queue_routing_key(self, celery_app):
        """Verify io_queue has correct routing key."""
        queues = celery_app.conf.task_queues
        io_queue = next((q for q in queues if q.name == "io_queue"), None)

        assert io_queue is not None
        assert io_queue.routing_key == "io"


class TestTaskRouting:
    """Test task routing to specialized queues."""

    @pytest.fixture
    def celery_app(self):
        """Import Celery app."""
        from app.celery_app import app

        return app

    def test_task_routes_configured(self, celery_app):
        """Verify task_routes is configured."""
        assert hasattr(celery_app.conf, "task_routes")
        assert celery_app.conf.task_routes is not None

    def test_ml_tasks_route_to_gpu_queue(self, celery_app):
        """Verify ML tasks (ml_*) route to gpu_queue."""
        task_routes = celery_app.conf.task_routes

        # Check for ml_* pattern routing
        ml_pattern_key = "app.tasks.ml_*"
        assert ml_pattern_key in task_routes
        assert task_routes[ml_pattern_key]["queue"] == "gpu_queue"

    def test_aggregate_tasks_route_to_cpu_queue(self, celery_app):
        """Verify aggregation tasks (aggregate_*) route to cpu_queue."""
        task_routes = celery_app.conf.task_routes

        # Check for aggregate_* pattern routing
        aggregate_pattern_key = "app.tasks.aggregate_*"
        assert aggregate_pattern_key in task_routes
        assert task_routes[aggregate_pattern_key]["queue"] == "cpu_queue"

    def test_upload_tasks_route_to_io_queue(self, celery_app):
        """Verify upload tasks (upload_*) route to io_queue."""
        task_routes = celery_app.conf.task_routes

        # Check for upload_* pattern routing
        upload_pattern_key = "app.tasks.upload_*"
        assert upload_pattern_key in task_routes
        assert task_routes[upload_pattern_key]["queue"] == "io_queue"

    def test_task_routes_count(self, celery_app):
        """Verify expected number of task route patterns."""
        task_routes = celery_app.conf.task_routes

        # Should have at least 3 route patterns (ml_*, aggregate_*, upload_*)
        assert len(task_routes) >= 3

    def test_ml_tasks_routing_configuration(self, celery_app):
        """Verify ML tasks routing configuration is complete."""
        task_routes = celery_app.conf.task_routes
        ml_route = task_routes.get("app.tasks.ml_*", {})

        # Verify queue is specified
        assert "queue" in ml_route
        assert ml_route["queue"] == "gpu_queue"

    def test_aggregate_tasks_routing_configuration(self, celery_app):
        """Verify aggregate tasks routing configuration is complete."""
        task_routes = celery_app.conf.task_routes
        aggregate_route = task_routes.get("app.tasks.aggregate_*", {})

        # Verify queue is specified
        assert "queue" in aggregate_route
        assert aggregate_route["queue"] == "cpu_queue"

    def test_upload_tasks_routing_configuration(self, celery_app):
        """Verify upload tasks routing configuration is complete."""
        task_routes = celery_app.conf.task_routes
        upload_route = task_routes.get("app.tasks.upload_*", {})

        # Verify queue is specified
        assert "queue" in upload_route
        assert upload_route["queue"] == "io_queue"


class TestWorkerStartupCommands:
    """Test worker startup command constants."""

    def test_gpu_worker_cmd_exists(self):
        """Verify GPU_WORKER_CMD constant exists."""
        from app.celery_app import GPU_WORKER_CMD

        assert GPU_WORKER_CMD is not None

    def test_cpu_worker_cmd_exists(self):
        """Verify CPU_WORKER_CMD constant exists."""
        from app.celery_app import CPU_WORKER_CMD

        assert CPU_WORKER_CMD is not None

    def test_io_worker_cmd_exists(self):
        """Verify IO_WORKER_CMD constant exists."""
        from app.celery_app import IO_WORKER_CMD

        assert IO_WORKER_CMD is not None

    def test_gpu_worker_uses_solo_pool(self):
        """CRITICAL: Verify GPU worker uses pool=solo (NOT prefork).

        GPU workers MUST use solo pool to prevent CUDA context conflicts.
        Using prefork causes "CUDA context already in use" errors.
        """
        from app.celery_app import GPU_WORKER_CMD

        # CRITICAL: Must use --pool=solo
        assert "--pool=solo" in GPU_WORKER_CMD

        # CRITICAL: Must NOT use prefork
        assert "--pool=prefork" not in GPU_WORKER_CMD
        assert "prefork" not in GPU_WORKER_CMD.lower()

    def test_gpu_worker_concurrency_one(self):
        """Verify GPU worker uses concurrency=1."""
        from app.celery_app import GPU_WORKER_CMD

        # GPU workers should have concurrency=1
        assert "--concurrency=1" in GPU_WORKER_CMD

    def test_gpu_worker_uses_gpu_queue(self):
        """Verify GPU worker listens to gpu_queue."""
        from app.celery_app import GPU_WORKER_CMD

        assert "--queues=gpu_queue" in GPU_WORKER_CMD

    def test_cpu_worker_uses_prefork_pool(self):
        """Verify CPU worker uses pool=prefork."""
        from app.celery_app import CPU_WORKER_CMD

        assert "--pool=prefork" in CPU_WORKER_CMD

    def test_cpu_worker_concurrency_four(self):
        """Verify CPU worker uses concurrency=4."""
        from app.celery_app import CPU_WORKER_CMD

        # CPU workers should have concurrency=4
        assert "--concurrency=4" in CPU_WORKER_CMD

    def test_cpu_worker_uses_cpu_queue(self):
        """Verify CPU worker listens to cpu_queue."""
        from app.celery_app import CPU_WORKER_CMD

        assert "--queues=cpu_queue" in CPU_WORKER_CMD

    def test_io_worker_uses_gevent_pool(self):
        """Verify I/O worker uses pool=gevent."""
        from app.celery_app import IO_WORKER_CMD

        assert "--pool=gevent" in IO_WORKER_CMD

    def test_io_worker_concurrency_fifty(self):
        """Verify I/O worker uses concurrency=50."""
        from app.celery_app import IO_WORKER_CMD

        # I/O workers should have concurrency=50
        assert "--concurrency=50" in IO_WORKER_CMD

    def test_io_worker_uses_io_queue(self):
        """Verify I/O worker listens to io_queue."""
        from app.celery_app import IO_WORKER_CMD

        assert "--queues=io_queue" in IO_WORKER_CMD

    def test_all_workers_use_celery_app(self):
        """Verify all workers reference app.celery_app."""
        from app.celery_app import CPU_WORKER_CMD, GPU_WORKER_CMD, IO_WORKER_CMD

        assert "-A app.celery_app" in GPU_WORKER_CMD
        assert "-A app.celery_app" in CPU_WORKER_CMD
        assert "-A app.celery_app" in IO_WORKER_CMD

    def test_all_workers_have_hostname(self):
        """Verify all workers have hostname configuration."""
        from app.celery_app import CPU_WORKER_CMD, GPU_WORKER_CMD, IO_WORKER_CMD

        assert "--hostname=" in GPU_WORKER_CMD
        assert "--hostname=" in CPU_WORKER_CMD
        assert "--hostname=" in IO_WORKER_CMD

    def test_gpu_worker_hostname_prefix(self):
        """Verify GPU worker has 'gpu@' hostname prefix."""
        from app.celery_app import GPU_WORKER_CMD

        assert "--hostname=gpu@%h" in GPU_WORKER_CMD

    def test_cpu_worker_hostname_prefix(self):
        """Verify CPU worker has 'cpu@' hostname prefix."""
        from app.celery_app import CPU_WORKER_CMD

        assert "--hostname=cpu@%h" in CPU_WORKER_CMD

    def test_io_worker_hostname_prefix(self):
        """Verify I/O worker has 'io@' hostname prefix."""
        from app.celery_app import IO_WORKER_CMD

        assert "--hostname=io@%h" in IO_WORKER_CMD


class TestGPUWorkerCriticalRequirements:
    """CRITICAL tests for GPU worker configuration.

    These tests verify that GPU workers are configured correctly to avoid
    CUDA context conflicts, which are a critical production issue (ADR-005).
    """

    def test_gpu_worker_pool_is_solo_not_prefork(self):
        """CRITICAL: GPU worker MUST use solo pool, NOT prefork.

        Prefork causes CUDA context conflicts. This is a MANDATORY requirement.
        """
        from app.celery_app import GPU_WORKER_CMD

        # CRITICAL: Must be solo
        assert "--pool=solo" in GPU_WORKER_CMD

        # CRITICAL: Must NOT be prefork
        assert "prefork" not in GPU_WORKER_CMD.lower()

    def test_gpu_worker_pool_is_solo_not_threads(self):
        """CRITICAL: GPU worker MUST use solo pool, NOT threads.

        Thread-based pools also cause CUDA issues.
        """
        from app.celery_app import GPU_WORKER_CMD

        # CRITICAL: Must be solo
        assert "--pool=solo" in GPU_WORKER_CMD

        # CRITICAL: Must NOT be threads
        assert "--pool=threads" not in GPU_WORKER_CMD
        assert (
            "threads" not in GPU_WORKER_CMD.lower()
            or "threads" in GPU_WORKER_CMD.lower()
            and "--pool=threads" not in GPU_WORKER_CMD
        )

    def test_gpu_worker_single_concurrency(self):
        """CRITICAL: GPU worker MUST have concurrency=1.

        Multiple concurrent GPU processes cause context conflicts.
        """
        from app.celery_app import GPU_WORKER_CMD

        assert "--concurrency=1" in GPU_WORKER_CMD

        # Verify NOT using higher concurrency
        assert "--concurrency=2" not in GPU_WORKER_CMD
        assert "--concurrency=4" not in GPU_WORKER_CMD

    def test_task_routing_sends_ml_to_gpu_queue(self):
        """CRITICAL: ML tasks MUST route to gpu_queue.

        If ML tasks route to CPU queue, they won't have GPU access.
        """
        from app.celery_app import app

        task_routes = app.conf.task_routes
        ml_route = task_routes.get("app.tasks.ml_*", {})

        assert ml_route.get("queue") == "gpu_queue"

    def test_gpu_queue_exists_for_routing(self):
        """CRITICAL: gpu_queue MUST exist for task routing.

        Without gpu_queue, ML tasks will fail to route.
        """
        from app.celery_app import app

        queues = app.conf.task_queues
        queue_names = [q.name for q in queues]

        assert "gpu_queue" in queue_names


class TestDefaultQueueConfiguration:
    """Test default queue settings."""

    @pytest.fixture
    def celery_app(self):
        """Import Celery app."""
        from app.celery_app import app

        return app

    def test_default_queue_is_default(self, celery_app):
        """Verify default queue is 'default'."""
        assert celery_app.conf.task_default_queue == "default"

    def test_default_exchange_is_default(self, celery_app):
        """Verify default exchange is 'default'."""
        assert celery_app.conf.task_default_exchange == "default"

    def test_default_routing_key_is_default(self, celery_app):
        """Verify default routing key is 'default'."""
        assert celery_app.conf.task_default_routing_key == "default"


class TestWorkerPoolTypes:
    """Test documentation and configuration of worker pool types."""

    def test_gpu_worker_not_using_unsupported_pools(self):
        """Verify GPU worker doesn't use unsupported pool types."""
        from app.celery_app import GPU_WORKER_CMD

        # Should NOT use these pool types
        unsupported_pools = ["prefork", "threads", "eventlet"]

        for pool_type in unsupported_pools:
            # If pool type is mentioned, it should NOT be the active pool
            if pool_type in GPU_WORKER_CMD:
                assert f"--pool={pool_type}" not in GPU_WORKER_CMD

    def test_cpu_worker_uses_optimal_pool(self):
        """Verify CPU worker uses prefork (optimal for CPU-bound tasks)."""
        from app.celery_app import CPU_WORKER_CMD

        # Prefork is optimal for CPU-bound tasks
        assert "--pool=prefork" in CPU_WORKER_CMD

    def test_io_worker_uses_optimal_pool(self):
        """Verify I/O worker uses gevent (optimal for I/O-bound tasks)."""
        from app.celery_app import IO_WORKER_CMD

        # Gevent is optimal for I/O-bound tasks
        assert "--pool=gevent" in IO_WORKER_CMD

    def test_each_worker_type_uses_different_pool(self):
        """Verify each worker type uses appropriate pool for workload."""
        from app.celery_app import CPU_WORKER_CMD, GPU_WORKER_CMD, IO_WORKER_CMD

        # Extract pool types
        gpu_pool = "solo" if "--pool=solo" in GPU_WORKER_CMD else None
        cpu_pool = "prefork" if "--pool=prefork" in CPU_WORKER_CMD else None
        io_pool = "gevent" if "--pool=gevent" in IO_WORKER_CMD else None

        # All should be configured
        assert gpu_pool == "solo"
        assert cpu_pool == "prefork"
        assert io_pool == "gevent"

        # All should be different (optimized for different workloads)
        pools = {gpu_pool, cpu_pool, io_pool}
        assert len(pools) == 3  # All unique


class TestQueueIsolation:
    """Test that queues are properly isolated for worker specialization."""

    @pytest.fixture
    def celery_app(self):
        """Import Celery app."""
        from app.celery_app import app

        return app

    def test_queues_have_separate_exchanges(self, celery_app):
        """Verify each queue has its own exchange for isolation."""
        queues = celery_app.conf.task_queues

        # Get non-default queues
        specialized_queues = [q for q in queues if q.name != "default"]

        # Each should have its own exchange
        exchange_names = {q.exchange.name for q in specialized_queues}

        # Should have at least 3 unique exchanges (gpu, cpu, io)
        assert len(exchange_names) >= 3
        assert "gpu" in exchange_names
        assert "cpu" in exchange_names
        assert "io" in exchange_names

    def test_routing_keys_match_queue_names(self, celery_app):
        """Verify routing keys align with queue purposes."""
        queues = celery_app.conf.task_queues

        # Check key queues
        gpu_queue = next((q for q in queues if q.name == "gpu_queue"), None)
        cpu_queue = next((q for q in queues if q.name == "cpu_queue"), None)
        io_queue = next((q for q in queues if q.name == "io_queue"), None)

        assert gpu_queue.routing_key == "gpu"
        assert cpu_queue.routing_key == "cpu"
        assert io_queue.routing_key == "io"
