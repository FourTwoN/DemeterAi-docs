# R020: S3 Image Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical`
- **Complexity**: L (5 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R019, R021, S017]
  - Blocked by: [F006, F007, DB011, R018]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L227-L245)

## Description

**What**: Implement repository class for `s3_images` table with CRUD operations, image_id UUID lookup, and **asyncpg COPY bulk insert** for high-volume uploads.

**Why**: S3 images store photo metadata (S3 keys, dimensions, EXIF, GPS). Repository provides image lookup, upload tracking, and bulk insert for batch uploads (critical for performance).

**Context**: image_id is UUID (PK). S3 keys are unique. Bulk insert via asyncpg COPY enables fast batch uploads (1000s of images). Used by photo gallery and ML pipeline.

## Acceptance Criteria

- [ ] **AC1**: `S3ImageRepository` class inherits from `AsyncRepository[S3Image]`
- [ ] **AC2**: Implements `get_by_image_id(image_id: UUID)` method (PK lookup)
- [ ] **AC3**: Implements `get_by_s3_key(s3_key: str)` method (unique constraint)
- [ ] **AC4**: Implements `get_by_user_id(user_id: int, limit: int)` for user galleries
- [ ] **AC5**: **CRITICAL**: Implements `bulk_insert_with_copy(images: List[dict])` using asyncpg COPY for performance
- [ ] **AC6**: Implements `get_failed_uploads()` for error recovery
- [ ] **AC7**: Query performance: UUID lookup <5ms, bulk insert <100ms for 100 images

## Technical Implementation Notes

**asyncpg COPY bulk insert** (CRITICAL for performance):

```python
async def bulk_insert_with_copy(
    self,
    images: List[dict]
) -> int:
    """Bulk insert images using asyncpg COPY (10-50x faster than ORM)"""
    from io import StringIO
    import csv

    # Create CSV in memory
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)

    for img in images:
        writer.writerow([
            str(img["image_id"]),  # UUID
            img["s3_bucket"],
            img["s3_key_original"],
            img.get("s3_key_thumbnail"),
            img["content_type"],
            img["file_size_bytes"],
            img["width_px"],
            img["height_px"],
            json.dumps(img.get("exif_metadata", {})),
            json.dumps(img.get("gps_coordinates", {})),
            img["upload_source"],
            img["uploaded_by_user_id"],
            img.get("status", "uploaded"),
            datetime.now(),
            datetime.now()
        ])

    csv_buffer.seek(0)

    # Use asyncpg raw connection for COPY
    async with self.session.connection() as conn:
        raw_conn = await conn.get_raw_connection()
        await raw_conn.driver_connection.copy_to_table(
            "s3_images",
            source=csv_buffer,
            columns=[
                "image_id", "s3_bucket", "s3_key_original",
                "s3_key_thumbnail", "content_type", "file_size_bytes",
                "width_px", "height_px", "exif_metadata", "gps_coordinates",
                "upload_source", "uploaded_by_user_id", "status",
                "created_at", "updated_at"
            ],
            format="csv"
        )

    return len(images)
```

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] **asyncpg COPY bulk insert tested with 100+ images**
- [ ] Performance benchmarks: COPY vs ORM insert (expect 10-50x speedup)
- [ ] UUID lookup tested
- [ ] S3 key uniqueness tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
