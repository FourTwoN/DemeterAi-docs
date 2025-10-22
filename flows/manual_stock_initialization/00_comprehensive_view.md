# Manual Stock Initialization - Comprehensive View

## Purpose

This diagram provides a high-level overview of the manual stock initialization workflow, showing all
major steps from user input to database persistence.

## Scope

- **Level:** Executive overview (~25 nodes)
- **Audience:** Product managers, architects, developers
- **Detail:** Simplified flow focusing on key validation points
- **Mermaid Version:** v11.3.0+ (modern syntax)

## What It Represents

The complete journey of a manual stock count through the system:

1. **User Input:** Form submission with product, packaging, quantity
2. **API Validation:** Pydantic schema validation
3. **Configuration Check:** CRITICAL validation against expected product/packaging
4. **Stock Creation:** Generate stock_movements + stock_batches
5. **Database Persistence:** Commit to PostgreSQL
6. **Response:** Return success or error

## Key Decision Points

### 1. Configuration Exists?

**If YES:**

- Validate product_id matches config
- Validate packaging_id matches config
- **Hard error** if mismatch (HTTP 400)

**If NO:**

- Allow manual initialization
- Optionally create config with user values

### 2. Product/Packaging Match?

**If YES:**

- Continue to stock creation

**If NO:**

- Raise ProductMismatchException or PackagingMismatchException
- Return HTTP 400 with user-friendly message

## Critical Path (Highlighted)

The diagram highlights the **happy path** in green:

```
Form Submit → API Validation → Config Check (PASS) → Create Stock → Return Success
```

Error paths shown in red:

- Product mismatch → HTTP 400
- Packaging mismatch → HTTP 400
- Validation error → HTTP 422

## Performance Annotations

- **Form Validation:** ~10ms (client-side)
- **API Validation:** ~20ms (Pydantic)
- **Config Check:** ~50ms (database query)
- **Stock Creation:** ~100ms (2 INSERT operations)
- **Total:** <200ms (synchronous, immediate response)

## Comparison with Photo Initialization

| Step              | Photo Init             | Manual Init                 |
|-------------------|------------------------|-----------------------------|
| **Upload**        | S3 (5-10 seconds)      | ❌ None                      |
| **ML Processing** | Celery (5-10 minutes)  | ❌ None                      |
| **Validation**    | ⚠️ Warning if mismatch | ❌ Hard error if mismatch    |
| **Response**      | Async (202 + polling)  | Synchronous (201 immediate) |

## How It Fits in the System

This workflow serves as an **alternative initialization method** alongside photo-based
initialization:

- **Use when:** Legacy data, small locations, photo unavailable
- **Avoid when:** Large locations, audit requirements, need size breakdown
- **Integration:** Works with monthly reconciliation just like photo init

## Related Diagrams

- **API Validation Detail:** [01_api_validation.md](./01_api_validation.md)
- **Config Check Detail:** [02_config_check.md](./02_config_check.md)
- **Batch Creation Detail:** [03_batch_creation.md](./03_batch_creation.md)

---

**Version:** 1.0
**Last Updated:** 2025-10-08
**Mermaid CLI Validation:** Required before commit
