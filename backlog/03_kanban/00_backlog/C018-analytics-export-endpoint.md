# [C018] Export Analytics - POST /api/analytics/export

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Export analytics results as Excel or CSV file.

## Acceptance Criteria

- [ ] **AC1**: Query params: format (excel/csv)
- [ ] **AC2**: Use same filters as /query endpoint
- [ ] **AC3**: Return StreamingResponse with file download

```python
from fastapi.responses import StreamingResponse

@router.post("/export")
async def export_analytics(
    request: AnalyticsQueryRequest,
    format: str = Query("excel", regex="^(excel|csv)$"),
    service: AnalyticsService = Depends()
):
    """Export analytics to Excel/CSV."""
    file_stream = await service.export_data(request, format)

    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if format == "excel"
        else "text/csv"
    )

    return StreamingResponse(
        file_stream,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=analytics.{format}"
        }
    )
```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
