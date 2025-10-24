"""
Unit tests for Photo Processing schemas.

Tests cover:
- PhotoUploadRequest validation
- PhotoUploadResponse validation
- Field constraints and types
- Error messages and Pydantic error handling
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.photo_schema import PhotoUploadJob, PhotoUploadRequest, PhotoUploadResponse


class TestPhotoUploadRequest:
    """Tests for PhotoUploadRequest schema."""

    def test_valid_request_small_file(self):
        """Test creating request with small file."""
        file_bytes = b"fake image data"
        request = PhotoUploadRequest(file=file_bytes)

        assert request.file == file_bytes
        assert isinstance(request.file, bytes)

    def test_valid_request_large_file(self):
        """Test creating request with large file."""
        file_bytes = b"x" * 1024 * 1024  # 1 MB
        request = PhotoUploadRequest(file=file_bytes)

        assert len(request.file) == 1024 * 1024

    def test_valid_request_empty_file(self):
        """Test creating request with empty file bytes."""
        file_bytes = b""
        request = PhotoUploadRequest(file=file_bytes)

        assert request.file == b""

    def test_valid_request_binary_data(self):
        """Test creating request with binary data."""
        file_bytes = bytes([0x89, 0x50, 0x4E, 0x47])  # PNG header
        request = PhotoUploadRequest(file=file_bytes)

        assert request.file == file_bytes

    def test_invalid_file_not_bytes(self):
        """Test that Pydantic will coerce string to bytes."""
        # Pydantic 2.x coerces str to bytes using UTF-8 encoding
        request = PhotoUploadRequest(file="test string")
        assert request.file == b"test string"

    def test_invalid_file_integer(self):
        """Test that file must be bytes, not integer."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadRequest(file=12345)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("file",) for err in errors)

    def test_missing_required_field_file(self):
        """Test that file is required."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadRequest()

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("file",) for err in errors)
        assert any(
            "missing" in str(err["msg"]).lower() or "required" in str(err["msg"]).lower()
            for err in errors
        )

    def test_model_dump(self):
        """Test serializing request to dict."""
        file_bytes = b"test"
        request = PhotoUploadRequest(file=file_bytes)

        data = request.model_dump()
        assert data["file"] == file_bytes

    def test_model_dump_json(self):
        """Test that bytes can be serialized to JSON (base64)."""
        file_bytes = b"test"
        request = PhotoUploadRequest(file=file_bytes)

        # Pydantic serializes bytes to base64 in JSON
        json_str = request.model_dump_json()
        assert '"file"' in json_str


class TestPhotoUploadResponse:
    """Tests for PhotoUploadResponse schema."""

    def _base_kwargs(self) -> dict[str, Any]:
        return {
            "upload_session_id": uuid4(),
            "task_id": uuid4(),
            "session_id": 1,
            "status": "pending",
            "message": "OK",
            "poll_url": "/api/v1/photos/jobs/status",
        }

    def test_valid_response_all_fields(self):
        """Test creating response with all valid fields."""
        job = PhotoUploadJob(
            job_id="celery-task-1",
            image_id=uuid4(),
            filename="photo.jpg",
            status="pending",
            progress_percent=0.0,
        )
        kwargs = self._base_kwargs()
        kwargs.update(
            {
                "session_id": 123,
                "message": "Photo uploaded successfully",
                "jobs": [job],
                "total_photos": 1,
                "estimated_time_seconds": 300,
            }
        )
        response = PhotoUploadResponse(**kwargs)

        assert response.task_id == kwargs["task_id"]
        assert isinstance(response.task_id, UUID)
        assert response.session_id == 123
        assert response.jobs[0].job_id == "celery-task-1"
        assert response.poll_url.startswith("/api/v1/photos/jobs/status")

    def test_valid_response_uuid_string(self):
        """Test creating response with UUID as string."""
        task_uuid = uuid4()
        kwargs = self._base_kwargs()
        kwargs.update(
            {
                "task_id": str(task_uuid),
                "session_id": 456,
                "status": "processing",
                "message": "Processing started",
                "poll_url": "/api/v1/photos/jobs/status?upload_session_id=123",
            }
        )
        response = PhotoUploadResponse(**kwargs)

        assert response.task_id == task_uuid
        assert isinstance(response.task_id, UUID)

    def test_valid_response_different_statuses(self):
        """Test response with different status values."""
        statuses = ["pending", "processing", "completed", "failed"]

        for status in statuses:
            kwargs = self._base_kwargs()
            kwargs.update({"status": status})
            response = PhotoUploadResponse(**kwargs)
            assert response.status == status

    def test_valid_response_long_message(self):
        """Test response with long message."""
        kwargs = self._base_kwargs()
        kwargs.update({"message": "x" * 1000})
        response = PhotoUploadResponse(**kwargs)

        assert len(response.message) == 1000

    def test_valid_response_url_formats(self):
        """Test response with different URL formats."""
        urls = [
            "/api/v1/photos/jobs/status",
            "http://localhost:8000/api/v1/photos/jobs/status",
            "https://example.com/photos/jobs/status",
            "/status?id=1",
        ]

        for url in urls:
            kwargs = self._base_kwargs()
            kwargs.update({"poll_url": url})
            response = PhotoUploadResponse(**kwargs)
            assert response.poll_url == url

    def test_invalid_task_id_not_uuid(self):
        """Test that task_id must be valid UUID."""
        kwargs = self._base_kwargs()
        kwargs.update({"task_id": "not-a-uuid"})

        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(**kwargs)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("task_id",) for err in errors)

    def test_invalid_session_id_string(self):
        """Test that session_id must be integer."""
        kwargs = self._base_kwargs()
        kwargs.update({"session_id": "not-an-int"})

        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(**kwargs)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("session_id",) for err in errors)

    def test_missing_required_field_upload_session(self):
        """Test that upload_session_id is required."""
        kwargs = self._base_kwargs()
        kwargs.pop("upload_session_id")

        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(**kwargs)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("upload_session_id",) for err in errors)

    def test_missing_required_field_task_id(self):
        """Test that task_id is required."""
        kwargs = self._base_kwargs()
        kwargs.pop("task_id")

        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(**kwargs)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("task_id",) for err in errors)

    def test_missing_required_field_status(self):
        """Test that status is required."""
        kwargs = self._base_kwargs()
        kwargs.pop("status")

        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(**kwargs)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("status",) for err in errors)

    def test_missing_required_field_message(self):
        """Test that message is required."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(
                task_id=uuid4(), session_id=1, status="pending", poll_url="/api/status"
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("message",) for err in errors)

    def test_missing_required_field_poll_url(self):
        """Test that poll_url is required."""
        with pytest.raises(ValidationError) as exc_info:
            kwargs = self._base_kwargs()
            kwargs.pop("poll_url")
            PhotoUploadResponse(**kwargs)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("poll_url",) for err in errors)

    def test_model_dump(self):
        """Test serializing response to dict."""
        kwargs = self._base_kwargs()
        kwargs.update({"session_id": 123, "message": "Processing"})
        response = PhotoUploadResponse(**kwargs)

        data = response.model_dump()
        assert UUID(data["upload_session_id"]) == kwargs["upload_session_id"]
        assert data["task_id"] == kwargs["task_id"]
        assert data["session_id"] == 123
        assert data["status"] == "pending"
        assert data["message"] == "Processing"
        assert data["poll_url"] == kwargs["poll_url"]

    def test_model_dump_json(self):
        """Test serializing response to JSON."""
        kwargs = self._base_kwargs()
        kwargs.update({"session_id": 123, "message": "Processing"})
        response = PhotoUploadResponse(**kwargs)

        json_str = response.model_dump_json()
        assert str(kwargs["task_id"]) in json_str
        assert '"session_id":123' in json_str
        assert '"status":"pending"' in json_str
