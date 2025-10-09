# Epic 013: Photo Upload & Gallery

**Status**: Ready
**Sprint**: Sprint-04 (Week 9-10)
**Priority**: medium (user experience)
**Total Story Points**: 40
**Total Cards**: 8

---

## Goal

Implement photo upload workflow with batch upload support, processing status tracking, gallery view, and error recovery mechanisms.

---

## Success Criteria

- [ ] Batch photo upload (up to 50 photos simultaneously)
- [ ] Real-time processing status via polling
- [ ] Gallery view with thumbnails
- [ ] Retry failed uploads
- [ ] EXIF metadata extraction (GPS, timestamp)
- [ ] Progress bar for multi-photo uploads

---

## Cards List (8 cards, 40 points)

### Upload Workflow (20 points)
- **PHOTO001**: Batch photo upload endpoint (8pts)
- **PHOTO002**: Multipart file handling (3pts)
- **PHOTO003**: EXIF metadata extraction (5pts)
- **PHOTO004**: S3 upload with progress tracking (4pts)

### Status & Monitoring (12 points)
- **PHOTO005**: Task status polling endpoint (3pts)
- **PHOTO006**: Processing status updates (3pts)
- **PHOTO007**: Error recovery & retry (4pts)
- **PHOTO008**: Upload history view (2pts)

### Gallery (8 points)
- **PHOTO009**: Gallery list endpoint (3pts)
- **PHOTO010**: Thumbnail generation (AVIF 400×400) (3pts)
- **PHOTO011**: Photo detail view (2pts)

---

## Dependencies

**Blocked By**: S023-S027 (Photo services), C001 (Upload controller)
**Blocks**: User onboarding, ML pipeline usage

---

## Technical Approach

**Batch Upload Flow**:
```
Client uploads 10 photos (multipart/form-data)
   ↓
API validates files (size, format)
   ↓
Spawn 10 Celery tasks (parallel S3 upload)
   ↓
Return task_ids[] for polling
   ↓
Client polls /tasks/status?task_ids=...
   ↓
Display progress bar (3/10 complete)
   ↓
ML processing triggered after upload
```

---

**Epic Owner**: Product Manager
**Created**: 2025-10-09
