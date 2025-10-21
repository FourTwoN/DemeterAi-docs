"""
Unit tests for Photo Processing schemas.

Tests cover:
- PhotoUploadRequest validation
- PhotoUploadResponse validation
- Field constraints and types
- Error messages and Pydantic error handling
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.photo_schema import PhotoUploadRequest, PhotoUploadResponse


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

    def test_valid_response_all_fields(self):
        """Test creating response with all valid fields."""
        task_uuid = uuid4()
        response = PhotoUploadResponse(
            task_id=task_uuid,
            session_id=123,
            status="pending",
            message="Photo uploaded successfully",
            poll_url="/api/sessions/123/status",
        )

        assert response.task_id == task_uuid
        assert isinstance(response.task_id, UUID)
        assert response.session_id == 123
        assert response.status == "pending"
        assert response.message == "Photo uploaded successfully"
        assert response.poll_url == "/api/sessions/123/status"

    def test_valid_response_uuid_string(self):
        """Test creating response with UUID as string."""
        task_uuid = uuid4()
        response = PhotoUploadResponse(
            task_id=str(task_uuid),
            session_id=456,
            status="processing",
            message="Processing started",
            poll_url="/api/sessions/456/status",
        )

        # Pydantic coerces string to UUID
        assert response.task_id == task_uuid
        assert isinstance(response.task_id, UUID)

    def test_valid_response_different_statuses(self):
        """Test response with different status values."""
        statuses = ["pending", "processing", "completed", "failed"]

        for status in statuses:
            response = PhotoUploadResponse(
                task_id=uuid4(),
                session_id=1,
                status=status,
                message=f"Status: {status}",
                poll_url="/api/sessions/1/status",
            )
            assert response.status == status

    def test_valid_response_large_session_id(self):
        """Test response with large session ID."""
        response = PhotoUploadResponse(
            task_id=uuid4(),
            session_id=999999,
            status="completed",
            message="Done",
            poll_url="/api/sessions/999999/status",
        )

        assert response.session_id == 999999

    def test_valid_response_long_message(self):
        """Test response with long message."""
        long_message = "x" * 1000
        response = PhotoUploadResponse(
            task_id=uuid4(),
            session_id=1,
            status="pending",
            message=long_message,
            poll_url="/api/sessions/1/status",
        )

        assert len(response.message) == 1000

    def test_valid_response_url_formats(self):
        """Test response with different URL formats."""
        urls = [
            "/api/sessions/1/status",
            "http://localhost:8000/api/sessions/1/status",
            "https://example.com/sessions/1",
            "/status?id=1",
        ]

        for url in urls:
            response = PhotoUploadResponse(
                task_id=uuid4(), session_id=1, status="pending", message="OK", poll_url=url
            )
            assert response.poll_url == url

    def test_invalid_task_id_not_uuid(self):
        """Test that task_id must be valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(
                task_id="not-a-uuid",
                session_id=1,
                status="pending",
                message="OK",
                poll_url="/api/status",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("task_id",) for err in errors)

    def test_invalid_task_id_integer(self):
        """Test that task_id must be UUID, not integer."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(
                task_id=12345, session_id=1, status="pending", message="OK", poll_url="/api/status"
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("task_id",) for err in errors)

    def test_invalid_session_id_string(self):
        """Test that session_id must be integer."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(
                task_id=uuid4(),
                session_id="not-an-int",
                status="pending",
                message="OK",
                poll_url="/api/status",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("session_id",) for err in errors)

    def test_valid_status_empty(self):
        """Test that status can be empty string (validation is at service layer)."""
        # Empty string is allowed by Pydantic - validation happens at service layer
        response = PhotoUploadResponse(
            task_id=uuid4(), session_id=1, status="", message="OK", poll_url="/api/status"
        )

        assert response.status == ""

    def test_missing_required_field_task_id(self):
        """Test that task_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(
                session_id=1, status="pending", message="OK", poll_url="/api/status"
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("task_id",) for err in errors)

    def test_missing_required_field_session_id(self):
        """Test that session_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(
                task_id=uuid4(), status="pending", message="OK", poll_url="/api/status"
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("session_id",) for err in errors)

    def test_missing_required_field_status(self):
        """Test that status is required."""
        with pytest.raises(ValidationError) as exc_info:
            PhotoUploadResponse(task_id=uuid4(), session_id=1, message="OK", poll_url="/api/status")

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
            PhotoUploadResponse(task_id=uuid4(), session_id=1, status="pending", message="OK")

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("poll_url",) for err in errors)

    def test_model_dump(self):
        """Test serializing response to dict."""
        task_uuid = uuid4()
        response = PhotoUploadResponse(
            task_id=task_uuid,
            session_id=123,
            status="pending",
            message="Processing",
            poll_url="/api/status",
        )

        data = response.model_dump()
        assert data["task_id"] == task_uuid
        assert data["session_id"] == 123
        assert data["status"] == "pending"
        assert data["message"] == "Processing"
        assert data["poll_url"] == "/api/status"

    def test_model_dump_json(self):
        """Test serializing response to JSON."""
        task_uuid = uuid4()
        response = PhotoUploadResponse(
            task_id=task_uuid,
            session_id=123,
            status="pending",
            message="Processing",
            poll_url="/api/status",
        )

        json_str = response.model_dump_json()
        assert f'"{task_uuid}"' in json_str
        assert '"session_id":123' in json_str
        assert '"status":"pending"' in json_str
