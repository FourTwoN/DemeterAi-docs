# Definition of Ready (DoR) - DemeterAI v2.0

## Checklist Before Card Enters Sprint

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**⚠️ Purpose**: Cards must meet DoR before sprint planning. Prevents mid-sprint blockers.

---

## What is Definition of Ready?

**DoR** defines criteria a card MUST meet before it can be:

1. Selected for a sprint during sprint planning
2. Moved from `03_kanban/00_backlog/` to `03_kanban/01_ready/`
3. Assigned to a developer

**Why DoR Matters**:

- Prevents starting work with unclear requirements
- Reduces mid-sprint blockers and delays
- Ensures team understands acceptance criteria
- Enables accurate story point estimation

---

## DoR Checklist

### ✅ 1. Clear Title & Description

**Requirements**:

- [ ] Card title is descriptive and action-oriented
- [ ] Description explains **what** needs to be done
- [ ] Description explains **why** (business/technical justification)
- [ ] Context provided (related features, decisions)

**Example**:

```markdown
# ✅ GOOD
## [ML003] Implement SAHI Tiled Detection for Segments

Description:
Implement SAHI (Slicing Aided Hyper Inference) for large segment detection...

Why: Large segments (>3000px) cannot be processed in single pass without
losing detail. SAHI provides 6.8% AP improvement for high-res images.

# ❌ BAD
## [ML003] Add SAHI

Description: Use SAHI

Why: (empty)
```

---

### ✅ 2. Acceptance Criteria (AC)

**Requirements**:

- [ ] At least 3-5 specific, testable acceptance criteria
- [ ] Each AC is measurable (not subjective)
- [ ] Each AC can be verified (manual test or automated test)
- [ ] Edge cases covered (error handling, validation)
- [ ] Non-functional requirements included (performance, security)

**Example**:

```markdown
# ✅ GOOD
Acceptance Criteria:
- [ ] SAHI slices segments into 640x640 tiles with 20% overlap
- [ ] Detections merged using GREEDYNMM (IOU threshold 0.5)
- [ ] Black tiles skipped (>98% black pixels)
- [ ] Processing time ≤4s for 3000x1500px segment
- [ ] Unit tests cover happy path + error cases (≥85% coverage)

# ❌ BAD
Acceptance Criteria:
- [ ] SAHI works
- [ ] Fast performance
- [ ] Tests exist
```

---

### ✅ 3. Dependencies Resolved

**Requirements**:

- [ ] All blocking cards listed in `Blocked by:` section
- [ ] All blocking cards are either:
    - Already completed (`05_done/`)
    - OR in same sprint with clear sequencing
- [ ] No circular dependencies
- [ ] External dependencies documented (e.g., GPU hardware, test data)

**Example**:

```markdown
# ✅ GOOD
Dependencies:
- Blocks: [ML005-estimation, ML009-coordinator]
- Blocked by: [ML002-segmentation, DB010-detections-model]
- Status: ML002 completed ✓, DB010 in sprint 01 (week before)

# ❌ BAD
Dependencies:
- Blocked by: [ML002]
- Status: (unknown - is ML002 done? when?)
```

---

### ✅ 4. Linked to Related Documentation

**Requirements**:

- [ ] At least 2-3 links to relevant docs
- [ ] Links include:
    - Engineering plan section (if applicable)
    - Flow diagram (if workflow-related)
    - Database schema (if data model changes)
    - Past decisions (if relevant)

**Example**:

```markdown
# ✅ GOOD
Related Documentation:
- Engineering Plan: ../../engineering_plan/backend/ml_pipeline.md
- Flow Diagram: ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md
- Database Schema: ../../database/database.mmd (lines 260-280)
- Past Decision: ../../context/past_chats_summary.md (lines 400-450)

# ❌ BAD
Related Documentation:
- See engineering plan
```

---

### ✅ 5. Sized (Story Points Assigned)

**Requirements**:

- [ ] Complexity estimated using Fibonacci scale (S=1-2, M=3-5, L=8, XL=13)
- [ ] Size reflects **effort**, not time (accounts for unknowns)
- [ ] Team consensus during planning poker (if complex)
- [ ] If XL (13 points), card should be broken down into multiple cards

**Sizing Guide**:

| Size   | Points | Description                          | Example                                           |
|--------|--------|--------------------------------------|---------------------------------------------------|
| **S**  | 1-2    | Simple, well-understood              | Add logging to existing service                   |
| **M**  | 3-5    | Moderate complexity, some unknowns   | Implement new service with 3-4 methods            |
| **L**  | 8      | Complex, multiple components         | ML pipeline coordinator (orchestrates 5 services) |
| **XL** | 13     | Very complex, break down if possible | Full YOLO integration (consider splitting)        |

**Example**:

```markdown
# ✅ GOOD
Complexity: M (3-5 points)
Justification: SAHI integration is moderate - library well-documented,
but need to handle tile merging and black tile filtering (some unknowns).

# ❌ BAD
Complexity: (not sized)
```

---

### ✅ 6. Technical Approach Outlined

**Requirements**:

- [ ] Key classes/functions to create listed
- [ ] Design pattern noted (if applicable)
- [ ] Architecture layer identified (Repository | Service | Controller | Task)
- [ ] Code hints provided (NOT full code, just signatures or patterns)

**Example**:

```markdown
# ✅ GOOD
Technical Implementation Notes:
- Layer: Service
- Pattern: SAHI library wrapper
- Key function: `detect_with_sahi(image_path, detector, config)`
- Hint: Use `get_sliced_prediction()` from SAHI, configure slicing params

# ❌ BAD
Technical Implementation Notes: (empty)
```

---

### ✅ 7. Testing Requirements Defined

**Requirements**:

- [ ] Unit test expectations listed (what to test)
- [ ] Integration test requirements (if applicable)
- [ ] Coverage target specified (≥80% for new code)
- [ ] Test template referenced (if standard pattern)

**Example**:

```markdown
# ✅ GOOD
Testing Requirements:
- Unit Tests:
  - Test SAHI slicing with 3000x1500px mock image
  - Test black tile filtering (expect 7 tiles skipped)
  - Test detection merging (verify NMS removes duplicates)
- Integration Tests:
  - Test with real photo from test fixtures
- Coverage: ≥85%
- Template: 04_templates/test-templates/test_service_template.py

# ❌ BAD
Testing Requirements:
- Write tests
```

---

### ✅ 8. Handover Briefing Included

**Requirements**:

- [ ] Context for next developer (why this exists)
- [ ] Key decisions documented
- [ ] Known limitations stated
- [ ] Next steps after completion identified

**Example**:

```markdown
# ✅ GOOD
Handover Briefing:
- Context: SAHI required for segments >3000px to maintain detection quality
- Decision: Use 640x640 tiles (not 512x512) for better speed/accuracy tradeoff
- Limitation: SAHI adds ~2-3s overhead vs direct detection
- Next steps: ML005-estimation depends on this card

# ❌ BAD
Handover Briefing: (empty)
```

---

## DoR Verification Process

### During Backlog Refinement

**When**: Mid-sprint (before next sprint planning)

**Who**: Product Owner + Tech Lead + 1-2 developers

**Steps**:

1. Review all cards in `03_kanban/00_backlog/`
2. For each card, check DoR checklist (8 items above)
3. If card passes DoR → move to `03_kanban/01_ready/`
4. If card fails DoR → update card with missing info OR park until info available

**Outcome**: `01_ready/` folder has 80-100 story points ready for next sprint

### During Sprint Planning

**When**: First day of sprint

**Who**: Entire team

**Steps**:

1. Review sprint goal
2. Select cards from `03_kanban/01_ready/` (all cards should already meet DoR)
3. Quick DoR verification (spot check)
4. If card fails DoR → back to backlog, select different card
5. Assign cards to developers

**Outcome**: Sprint backlog with DoR-compliant cards

---

## Common DoR Violations (and How to Fix)

### ❌ Violation 1: Vague Acceptance Criteria

**Problem**:

```markdown
Acceptance Criteria:
- [ ] Code works
- [ ] Tests pass
```

**Fix**:

```markdown
Acceptance Criteria:
- [ ] `detect_with_sahi()` returns list of detection dicts with bbox, confidence
- [ ] Black tiles skipped (>98% black pixels)
- [ ] Processing time ≤4s for 3000x1500px segment
- [ ] Unit test coverage ≥85%
- [ ] Integration test passes with test photo fixture
```

### ❌ Violation 2: Missing Dependencies

**Problem**:

```markdown
Dependencies: (empty)
```

**Fix**:

```markdown
Dependencies:
- Blocks: [ML005-estimation, ML009-coordinator]
- Blocked by: [ML002-segmentation ✓, DB010-detections-model ✓]
- External: Requires YOLO model weights (yolov11m.pt, 50MB download)
```

### ❌ Violation 3: No Size Estimate

**Problem**:

```markdown
Complexity: (not sized)
```

**Fix**:

```markdown
Complexity: M (3-5 points)
Justification: SAHI integration is moderate - well-documented library,
but need to handle tile merging (some complexity). Team consensus: 5 points.
```

### ❌ Violation 4: No Links to Docs

**Problem**:

```markdown
Related Documentation: (none)
```

**Fix**:

```markdown
Related Documentation:
- Engineering Plan: ../../engineering_plan/backend/ml_pipeline.md (lines 150-200)
- Flow Diagram: ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md
- SAHI GitHub: https://github.com/obss/sahi (external reference OK)
```

---

## DoR Checklist Summary (Quick Reference)

Print this and use during backlog refinement:

```
DEFINITION OF READY (DoR) - Quick Checklist

Card ID: [________]  Card Title: [_________________________]

[ ] 1. Clear title & description (what, why, context)
[ ] 2. Acceptance criteria (3-5 specific, testable)
[ ] 3. Dependencies resolved (blockers cleared or in sprint)
[ ] 4. Linked to docs (2-3 relevant links)
[ ] 5. Sized (S/M/L/XL, consensus if needed)
[ ] 6. Technical approach outlined (layer, pattern, hints)
[ ] 7. Testing requirements defined (unit, integration, coverage)
[ ] 8. Handover briefing included (context, decisions, next steps)

PASS = All 8 checked → Move to 01_ready/
FAIL = Missing items → Update card OR park in backlog

Reviewer: [________]  Date: [________]
```

---

## References

- **Card Template**: See example cards in `03_kanban/00_backlog/`
- **Acceptance Criteria Examples**: See `03_kanban/00_backlog/ML003-sahi-detection.md`
- **Sizing Guide**: See `00_foundation/team-capacity.md`

---

**Document Owner**: Product Owner + Tech Lead
**Review Frequency**: Every sprint retrospective (adjust criteria if needed)
**Enforcement**: Sprint planning facilitator enforces DoR compliance
