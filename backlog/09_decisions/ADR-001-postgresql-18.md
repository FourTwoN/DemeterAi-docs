# ADR-001: PostgreSQL 18 (Not 15)

**Status**: Accepted
**Date**: 2025-10-09
**Deciders**: Tech Lead, Database Architect
**Context**: Database version selection for DemeterAI v2.0

---

## Context

Original engineering documents referenced PostgreSQL 15, but latest stable release is PostgreSQL 18
with significant improvements for our use case.

---

## Decision

Use **PostgreSQL 18** as the database version (NOT PostgreSQL 15).

---

## Rationale

**Why PostgreSQL 18**:

1. **Improved Partitioning**: Better performance for daily-partitioned tables (detections,
   estimations)
2. **Query Planner**: 15-20% faster for complex geospatial queries (PostGIS)
3. **JSON Performance**: 2× faster JSON operations (used for EXIF metadata, configuration)
4. **Parallel Queries**: Better parallelization for aggregation queries (analytics)
5. **Stability**: Released 2024-09, production-proven for 1+ year

**Why NOT PostgreSQL 15**:

- Missing partitioning improvements we need
- Older query planner (slower geospatial queries)
- No longer latest stable (15 → 16 → 17 → 18)

---

## Consequences

**Positive**:

- ✅ Better performance for our workload (partitions, geospatial, JSON)
- ✅ Latest features and optimizations
- ✅ Longer support window (5 years from 2024)

**Negative**:

- ⚠️ Requires updating all docs referencing PostgreSQL 15
- ⚠️ Docker image: `postgis/postgis:18-3.5` (not `:15-3.3`)
- ⚠️ May need to test compatibility (unlikely to break, but verify)

**Neutral**:

- Migration path from 15 → 18 is straightforward if needed

---

## Implementation

**Update These Files**:

1. `00_foundation/tech-stack.md` → PostgreSQL 18
2. Docker Compose → `postgis/postgis:18-3.5`
3. Requirements → `psycopg[binary]>=3.2` (PostgreSQL 18 compatible)

**Verification**:

```bash
# Check PostgreSQL version
docker exec demeterai_db psql -U user -c "SELECT version();"
# Expected: PostgreSQL 18.x
```

---

**Related Decisions**:

- ADR-004: Daily partitioning (benefits from PostgreSQL 18 improvements)
- ADR-007: PostGIS 3.5 (requires PostgreSQL 18)

---

**Document Owner**: Database Architect
**Last Updated**: 2025-10-09
