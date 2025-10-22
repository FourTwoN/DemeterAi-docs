# API Entry Detailed Flow

## Purpose

This diagram provides a **line-by-line code flow** for the FastAPI POST /api/stock/photo controller,
showing every validation step, database operation, and Celery task dispatch with actual Python code
snippets.

## Scope

- **Level**: Ultra-detail (implementation code)
- **Audience**: Developers implementing or debugging the API endpoint
- **Detail**: Every function call, error path, database transaction, async operation
- **Mermaid Version**: v11.3.0+

## What It Represents

The complete API entry point including:

1. **Request Extraction**: MultipartForm parsing, file list extraction
2. **Validation**: File count limits, content type, size (< 50MB), extensions
3. **UUID Generation**: Application-level UUID v4 (not database SERIAL)
4. **Temporary Storage**: Save to `/tmp/uploads/`, optional metadata JSON
5. **S3 Key Generation**: Date-based path structure `original/YYYY/MM/DD/uuid.jpg`
6. **Database INSERT**: Batch insert to `s3_images` table with transaction
7. **Task Chunking**: S3 chunks of 20 images, ML tasks 1:1
8. **Celery Dispatch**: Parallel task groups for S3 and ML workers
9. **Response Building**: 202 Accepted with task IDs for polling

## Key Design Decisions

### UUID as Primary Key (Application-Generated)

**Decision**: Generate UUID in application code, NOT database SERIAL

**Rationale**:

- **Idempotency**: Same UUID for retries
- **Distributed Systems**: No central ID generator needed
- **S3 Key Predictability**: Know S3 path before upload
- **No DB Round-Trip**: Generate ID without querying database

**Code**:

```python
import uuid
image_id = uuid.uuid4()  # Generated in API, used everywhere
```

### Batch Database Commit

**Decision**: Insert all records in loop, commit once at end

**Benefit**: 10x faster than per-row commits

**Code**:

```python
for photo in photos:
    session.add(s3_image)  # Add to session
    # No commit here
await session.commit()  # Single batch commit
```

### Task Chunking Strategy

**S3 Tasks**: 20 images per chunk (I/O bound, efficient batching)
**ML Tasks**: 1 image per task (GPU bound, parallel processing)

### Error Handling - 207 Multi-Status

Returns partial success if some files fail validation:

```json
{
  "success": ["uuid1", "uuid2"],
  "errors": [{"index": 2, "error": "Invalid format"}],
  "successful": 2,
  "failed": 1
}
```

## Performance

| Step                  | Duration       | Notes                         |
|-----------------------|----------------|-------------------------------|
| Extract files         | ~10ms          | FastAPI multipart parsing     |
| Validate each file    | ~5ms           | Content-type, size, extension |
| Generate UUID         | ~0.1ms         | uuid.uuid4() very fast        |
| Save temp file        | ~10-20ms       | Disk I/O (async)              |
| DB INSERT (each)      | ~20-30ms       | PostgreSQL connection pool    |
| Batch commit          | ~50ms          | Single transaction            |
| Dispatch tasks        | ~10ms          | Celery group()                |
| Build response        | ~2ms           | JSON serialization            |
| **Total (10 photos)** | **~250-350ms** | Scales linearly               |

## Error Paths

1. **No files provided** → 400 Bad Request
2. **Too many files (> 100)** → 400 Bad Request
3. **Invalid file type** → Collect error, continue
4. **File too large (> 50MB)** → Collect error, continue
5. **Database insert fails** → Rollback, collect error
6. **Some files valid, some invalid** → 207 Multi-Status (partial success)

## Related Diagrams

- **Master Overview**: `flows/00_master_overview.mmd` (high-level context)
- **Complete Pipeline v4**: `flows/01_complete_pipeline_v4.mmd` (full system)
- **S3 Upload Task**: `flows/03_s3_upload_circuit_breaker_detailed.mmd` (next step)

## How It Fits in the System

This is the **entry point** for the entire ML pipeline:

- User uploads photos via web/mobile
- API validates, saves temp files, creates DB records
- Dispatches async tasks (S3 upload + ML processing)
- Returns immediately with task IDs
- Client polls `/api/stock/tasks/status` for results

## Code Patterns Used

### Async File I/O

```python
import aiofiles
async with aiofiles.open(path, 'wb') as f:
    await f.write(content)
```

### SQLAlchemy Async Session

```python
async with get_async_session() as session:
    session.add(s3_image)
    await session.commit()
```

### Celery Group Pattern

```python
from celery import group
task_group = group(
    task.s(arg).set(queue='queue_name')
    for arg in args
)
result = task_group.apply_async()
```

---

**Version**: 1.0
**Last Updated**: 2025-10-07
**Lines of Code**: ~60 nodes
**Author**: DemeterAI Engineering Team
