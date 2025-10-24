"""Integration tests for S3 bucket migration script.

This module tests the migration script that moves visualization images from
the old viz bucket (demeter-photos-viz) to the new single-bucket structure
with folder organization (demeter-photos-original/{session_id}/processed.{ext}).

Test Coverage:
- Dry-run mode (no actual changes)
- Live migration mode (actual moves)
- Error handling (S3 failures, database errors)
- Progress reporting
- Rollback scenarios

Architecture:
    Layer: Integration Testing (Data Migration)
    Pattern: Real database + mocked S3
    Fixtures: db_session, mock S3 client

Note:
    Uses real PostgreSQL database to verify migration correctness.
    Mocks S3 operations to avoid dependency on AWS credentials.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.models.s3_image import ContentTypeEnum, ProcessingStatusEnum
from app.repositories.s3_image_repository import S3ImageRepository

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client for migration testing."""
    mock_client = MagicMock()
    mock_client.get_object.return_value = {
        "Body": MagicMock(read=lambda: b"fake_viz_image_data"),
        "ContentType": "image/avif",
    }
    mock_client.put_object.return_value = {"ETag": '"migrated123"'}
    mock_client.delete_object.return_value = {"DeleteMarker": False}
    return mock_client


@pytest.fixture
async def old_viz_images(db_session):
    """Create sample old-style visualization images for migration testing.

    Returns:
        list[S3Image]: 3 old viz images in demeter-photos-viz bucket
    """
    s3_repo = S3ImageRepository(db_session)
    images = []

    for i in range(3):
        session_id = uuid.uuid4()
        image = await s3_repo.create(
            {
                "image_id": uuid.uuid4(),
                "s3_bucket": settings.S3_BUCKET_VISUALIZATION,  # OLD viz bucket
                "s3_key_original": f"{session_id}/viz_image_{i}.avif",
                "content_type": ContentTypeEnum.AVIF,
                "file_size_bytes": 1024 * (i + 1),
                "width_px": 1000,
                "height_px": 800,
                "upload_source": "api",
                "status": ProcessingStatusEnum.READY,
            }
        )
        images.append(image)

    return images


# =============================================================================
# Test Migration Script - Dry-Run Mode
# =============================================================================


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_dry_run(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script in dry-run mode (no actual changes made)."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    # Import migration script
    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act - Run migration in dry-run mode
    report = await migrate_viz_images(dry_run=True, db_session=db_session)

    # Assert - Verify no changes made
    assert report["dry_run"] is True
    assert report["total"] == 3  # 3 old viz images found
    assert report["migrated"] == 0  # No migrations in dry-run
    assert report["failed"] == 0

    # Verify S3 operations NOT called (dry-run)
    mock_s3_client.get_object.assert_not_called()
    mock_s3_client.put_object.assert_not_called()
    mock_s3_client.delete_object.assert_not_called()

    # Verify database NOT updated (dry-run)
    s3_repo = S3ImageRepository(db_session)
    for old_image in old_viz_images:
        updated_image = await s3_repo.get(old_image.image_id)
        assert updated_image.s3_bucket == settings.S3_BUCKET_VISUALIZATION  # Still old bucket


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_dry_run_shows_preview(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test dry-run mode shows preview of what would be migrated."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act
    report = await migrate_viz_images(dry_run=True, db_session=db_session)

    # Assert - Verify preview information
    assert "preview" in report
    assert len(report["preview"]) == 3

    # Verify preview contains migration details
    preview_item = report["preview"][0]
    assert "old_key" in preview_item
    assert "new_key" in preview_item
    assert "old_bucket" in preview_item
    assert preview_item["old_bucket"] == settings.S3_BUCKET_VISUALIZATION
    assert preview_item["new_bucket"] == settings.S3_BUCKET_ORIGINAL
    assert "/processed." in preview_item["new_key"]  # New naming pattern


# =============================================================================
# Test Migration Script - Live Run
# =============================================================================


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_live_run(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script live run (actual migration)."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act - Run migration in live mode
    report = await migrate_viz_images(dry_run=False, db_session=db_session)

    # Assert - Verify migrations completed
    assert report["dry_run"] is False
    assert report["total"] == 3
    assert report["migrated"] == 3
    assert report["failed"] == 0

    # Verify S3 operations called (download → upload → delete)
    assert mock_s3_client.get_object.call_count == 3  # Download 3 images
    assert mock_s3_client.put_object.call_count == 3  # Upload 3 images
    assert mock_s3_client.delete_object.call_count == 3  # Delete 3 old images

    # Verify database updated with new bucket/key
    s3_repo = S3ImageRepository(db_session)
    for old_image in old_viz_images:
        updated_image = await s3_repo.get(old_image.image_id)
        assert updated_image.s3_bucket == settings.S3_BUCKET_ORIGINAL  # NEW bucket
        assert "/processed." in updated_image.s3_key_processed  # NEW key pattern
        assert updated_image.image_type == "processed"  # NEW image_type field


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_updates_s3_key_pattern(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script updates S3 key from old pattern to new pattern."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Get old key pattern (before migration)
    old_image = old_viz_images[0]
    old_key = old_image.s3_key_original  # e.g., "{session_id}/viz_image_0.avif"
    session_id_str = old_key.split("/")[0]

    # Act
    await migrate_viz_images(dry_run=False, db_session=db_session)

    # Assert - Verify new key pattern
    s3_repo = S3ImageRepository(db_session)
    migrated_image = await s3_repo.get(old_image.image_id)
    new_key = migrated_image.s3_key_processed

    # New pattern: {session_id}/processed.{ext}
    assert new_key.startswith(session_id_str)
    assert "/processed." in new_key
    assert new_key.endswith(".avif")  # Preserves original extension

    # Verify upload to new key
    put_object_call = [
        call for call in mock_s3_client.put_object.call_args_list if call[1]["Key"] == new_key
    ][0]
    assert put_object_call[1]["Bucket"] == settings.S3_BUCKET_ORIGINAL


# =============================================================================
# Test Error Handling
# =============================================================================


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_handles_s3_download_failure(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script handles S3 download failures gracefully."""
    # Arrange
    mock_s3_client.get_object.side_effect = Exception("S3 download failed")
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act - Migration should continue despite failures
    report = await migrate_viz_images(dry_run=False, db_session=db_session)

    # Assert - All migrations failed (download errors)
    assert report["total"] == 3
    assert report["migrated"] == 0
    assert report["failed"] == 3

    # Verify error details captured
    assert "errors" in report
    assert len(report["errors"]) == 3
    assert all("download failed" in err.lower() for err in report["errors"])


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_handles_s3_upload_failure(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script handles S3 upload failures (doesn't delete old file)."""
    # Arrange - Download succeeds, upload fails
    mock_s3_client.put_object.side_effect = Exception("S3 upload failed")
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act
    report = await migrate_viz_images(dry_run=False, db_session=db_session)

    # Assert - All migrations failed (upload errors)
    assert report["migrated"] == 0
    assert report["failed"] == 3

    # Verify old files NOT deleted (safety measure)
    mock_s3_client.delete_object.assert_not_called()


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_handles_database_update_failure(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script handles database update failures."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    # Mock repository update to fail
    with patch("app.repositories.s3_image_repository.S3ImageRepository.update") as mock_update:
        mock_update.side_effect = Exception("Database error")

        from scripts.migrate_s3_viz_bucket import migrate_viz_images

        # Act
        report = await migrate_viz_images(dry_run=False, db_session=db_session)

        # Assert - Migrations failed at database update step
        assert report["failed"] == 3
        assert "errors" in report


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_partial_success(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script handles partial success (some succeed, some fail)."""
    # Arrange - First 2 succeed, 3rd fails
    call_count = [0]

    def download_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 3:
            raise Exception("S3 download failed for image 3")
        return {"Body": MagicMock(read=lambda: b"fake_data"), "ContentType": "image/avif"}

    mock_s3_client.get_object.side_effect = download_side_effect
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act
    report = await migrate_viz_images(dry_run=False, db_session=db_session)

    # Assert - Partial success
    assert report["total"] == 3
    assert report["migrated"] == 2  # First 2 succeeded
    assert report["failed"] == 1  # 3rd failed


# =============================================================================
# Test Migration Progress Reporting
# =============================================================================


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_reports_progress(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script reports progress during execution."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client
    progress_updates = []

    # Mock progress callback
    def progress_callback(current, total, message):
        progress_updates.append({"current": current, "total": total, "message": message})

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act
    await migrate_viz_images(
        dry_run=False, db_session=db_session, progress_callback=progress_callback
    )

    # Assert - Progress updates received
    assert len(progress_updates) == 3  # 3 images migrated
    assert progress_updates[0]["current"] == 1
    assert progress_updates[0]["total"] == 3
    assert progress_updates[-1]["current"] == 3
    assert progress_updates[-1]["total"] == 3


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_generates_summary_report(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script generates detailed summary report."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act
    report = await migrate_viz_images(dry_run=False, db_session=db_session)

    # Assert - Verify report structure
    assert "total" in report
    assert "migrated" in report
    assert "failed" in report
    assert "dry_run" in report
    assert "duration_seconds" in report
    assert "migrated_images" in report

    # Verify migrated images details
    migrated_details = report["migrated_images"]
    assert len(migrated_details) == 3

    detail = migrated_details[0]
    assert "image_id" in detail
    assert "old_key" in detail
    assert "new_key" in detail
    assert "file_size_bytes" in detail


# =============================================================================
# Test Idempotency (Running Migration Twice)
# =============================================================================


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_is_idempotent(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script can be run multiple times safely (idempotent)."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act - Run migration twice
    report1 = await migrate_viz_images(dry_run=False, db_session=db_session)
    report2 = await migrate_viz_images(dry_run=False, db_session=db_session)

    # Assert - Second run finds no images to migrate (already migrated)
    assert report1["migrated"] == 3
    assert report2["migrated"] == 0  # Nothing left to migrate
    assert report2["total"] == 0  # No old viz images found


# =============================================================================
# Test Rollback Capability
# =============================================================================


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_rollback(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script can rollback changes (restore old state)."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client

    from scripts.migrate_s3_viz_bucket import migrate_viz_images, rollback_migration

    # Act - Migrate then rollback
    report = await migrate_viz_images(dry_run=False, db_session=db_session)
    rollback_report = await rollback_migration(
        migration_report=report, db_session=db_session, mock_s3_client=mock_s3_client
    )

    # Assert - Rollback restored old state
    assert rollback_report["rolled_back"] == 3

    # Verify database restored to old bucket
    s3_repo = S3ImageRepository(db_session)
    for old_image in old_viz_images:
        restored_image = await s3_repo.get(old_image.image_id)
        assert restored_image.s3_bucket == settings.S3_BUCKET_VISUALIZATION  # OLD bucket restored


# =============================================================================
# Test Migration Filter (Migrate Only Specific Session)
# =============================================================================


@pytest.mark.asyncio
@patch("scripts.migrate_s3_viz_bucket.boto3.client")
async def test_migration_script_filter_by_session(
    mock_boto3_client, db_session, old_viz_images, mock_s3_client
):
    """Test migration script can filter by session_id (migrate only specific sessions)."""
    # Arrange
    mock_boto3_client.return_value = mock_s3_client
    target_session_id = old_viz_images[0].s3_key_original.split("/")[0]

    from scripts.migrate_s3_viz_bucket import migrate_viz_images

    # Act - Migrate only target session
    report = await migrate_viz_images(
        dry_run=False, db_session=db_session, session_id_filter=target_session_id
    )

    # Assert - Only 1 image migrated (target session)
    assert report["total"] == 1
    assert report["migrated"] == 1
