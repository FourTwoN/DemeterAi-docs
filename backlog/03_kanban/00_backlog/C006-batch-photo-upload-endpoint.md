# [C006] Batch Photo Upload - POST /api/photos/upload

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocked by: [C001, SVC001]

## Description

Upload multiple photos in a single request for batch processing.

## Acceptance Criteria

- [ ] **AC1**: Accept multipart form with multiple files (max 10 per request)
- [ ] **AC2**: Validate each file (type, size)
- [ ] **AC3**: Return array of task_ids
- [ ] **AC4**: HTTP 207 Multi-Status for partial failures

```python
@router.post("/upload", response_model=List[PhotoUploadResponse])
async def batch_upload_photos(
    files: List[UploadFile] = File(...),
    service: PhotoService = Depends()
):
    """Upload multiple photos (max 10)."""
    if len(files) > 10:
        raise HTTPException(413, "Max 10 files per request")

    results = []
    for file in files:
        result = await service.create_photo_session(file)
        results.append(result)

    return results
```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
