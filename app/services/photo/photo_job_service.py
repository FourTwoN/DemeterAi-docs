"""Photo job tracking service using Redis."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis  # type: ignore[import-not-found]

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger

logger = get_logger(__name__)


class PhotoJobService:
    """Service responsible for tracking photo processing jobs in Redis."""

    SESSION_KEY_PREFIX = "upload_session"
    JOB_STATUS_PREFIX = "job_status"

    async def create_upload_session(
        self,
        redis: Redis,
        upload_session_id: str,
        user_id: int | None,
        jobs: list[dict[str, Any]],
    ) -> None:
        """Store upload session metadata in Redis."""
        key = f"{self.SESSION_KEY_PREFIX}:{upload_session_id}"
        payload = {
            "upload_session_id": upload_session_id,
            "user_id": user_id,
            "jobs": jobs,
            "created_at": datetime.now(UTC).isoformat(),
        }

        logger.debug(
            "Caching upload session metadata",
            extra={"redis_key": key, "jobs": len(jobs)},
        )
        await redis.setex(
            key,
            settings.REDIS_UPLOAD_SESSION_TTL,
            json.dumps(payload),
        )

    async def get_session_status(
        self,
        redis: Redis,
        upload_session_id: str,
    ) -> dict[str, Any]:
        """Retrieve job statuses for an upload session."""
        key = f"{self.SESSION_KEY_PREFIX}:{upload_session_id}"
        cached = await redis.get(key)

        if not cached:
            raise ResourceNotFoundException(
                resource_type="UploadSession",
                resource_id=upload_session_id,
            )

        session_data = json.loads(cached)
        jobs_meta: list[dict[str, Any]] = session_data.get("jobs", [])

        jobs: list[dict[str, Any]] = []
        summary = {
            "total_jobs": len(jobs_meta),
            "completed": 0,
            "processing": 0,
            "pending": 0,
            "failed": 0,
            "overall_progress_percent": 0.0,
        }

        for job_meta in jobs_meta:
            job_id = job_meta.get("job_id")
            job_status_key = f"{self.JOB_STATUS_PREFIX}:{job_id}"
            job_status_raw = await redis.get(job_status_key)

            if job_status_raw:
                job_status = json.loads(job_status_raw)
            else:
                job_status = {"job_id": job_id, "status": "pending", "progress_percent": 0}

            # Merge metadata with dynamic status
            merged = {**job_meta, **job_status}
            status = merged.get("status", "pending")
            progress = merged.get("progress_percent", 0) or 0

            summary.setdefault(status, 0)
            summary[status] = summary.get(status, 0) + 1  # type: ignore[assignment]

            if "progress_percent" not in merged:
                merged["progress_percent"] = progress

            jobs.append(merged)

        completed_or_failed = summary.get("completed", 0) + summary.get("failed", 0)
        total_jobs = summary["total_jobs"]
        if total_jobs > 0:
            summary["overall_progress_percent"] = round(
                (completed_or_failed / total_jobs) * 100,
                2,
            )

        return {
            "upload_session_id": upload_session_id,
            "jobs": jobs,
            "summary": summary,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    async def update_job_status(
        self,
        redis: Redis,
        job_id: str,
        status: str,
        **extra: Any,
    ) -> None:
        """Update single job status in Redis."""
        key = f"{self.JOB_STATUS_PREFIX}:{job_id}"
        payload = {
            "job_id": job_id,
            "status": status,
            "updated_at": datetime.now(UTC).isoformat(),
            **extra,
        }
        logger.debug("Updating job status", extra={"job_id": job_id, "status": status})
        await redis.setex(
            key,
            settings.REDIS_JOB_STATUS_TTL,
            json.dumps(payload),
        )
