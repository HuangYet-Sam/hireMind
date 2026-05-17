# HireMind Backend Architecture Review

**Date:** 2026-05-17
**Reviewer:** 架构师
**Scope:** `packages/api/` — FastAPI + SQLAlchemy async + asyncpg + Alembic
**Coverage:** 9 Services, 8 Routers, 12 Models, 8 Schemas, Middleware, Dependencies, Migrations, Tests, Deployment

---

## Executive Summary

| Severity | Count |
|----------|-------|
| **Critical** | 12 |
| **Major** | 19 |
| **Minor** | 15 |

The codebase follows a clean layered architecture (Router → Service → Model) with consistent naming conventions and good use of async patterns. However, several critical issues require immediate attention before production deployment: authentication bypass defaults, missing RBAC enforcement, cascading eager-load N+1 queries, and missing database indexes on foreign keys.

---

## Critical Issues (P0 — Must Fix Before Production)

### C-01: Authentication Bypass Default
**Files:** `app/middleware/auth.py:61-63`, `app/dependencies.py:84-86`

`get_current_user()` returns a hardcoded `dev_user/admin` when no auth header is present. This means **every unauthenticated request gets admin access** in any environment where middleware is active.

```python
# Current (dangerous):
if not user_id:
    user_id = "dev_user"
    tenant_id = "default"
    role = "admin"
```

**Fix:** Raise `HTTPException(401)` when no credentials are provided. Gate behind a `DEBUG` or `ENV=development` flag if needed for local dev.

---

### C-02: Zero RBAC Enforcement
**Files:** All 8 router files

`require_role()` is defined in `dependencies.py` but **never used by any endpoint**. Every authenticated user can create, update, delete any resource, approve offers, and access analytics.

**Fix:** Add role-based dependencies to all mutating endpoints. At minimum:
- `POST/PUT/DELETE` → `require_role("admin", "hr_manager")`
- `approve` on offers → `require_role("admin", "hr_manager", "director")`
- `GET /analytics/*` → `require_role("admin", "hr_manager")`

---

### C-03: Cascading Eager-Load N+1 (selectin Bomb)
**Files:** All model files with relationships

Every relationship uses `lazy="selectin"` unconditionally. A single `list_positions()` query triggers:
```
SELECT * FROM positions WHERE ...
SELECT * FROM departments WHERE id IN (...)     -- via position.department
SELECT * FROM candidates WHERE position_id IN (...)  -- via department.candidates
SELECT * FROM resumes WHERE candidate_id IN (...)    -- via candidate.resumes
SELECT * FROM interviews WHERE candidate_id IN (...)  -- via candidate.interviews
SELECT * FROM offers WHERE candidate_id IN (...)      -- via candidate.offers
```

One list endpoint can produce **thousands of SQL queries**.

**Fix:**
1. Change all relationships to `lazy="raise"` to prevent implicit loads
2. Use explicit `selectinload()` / `subqueryload()` only where needed per query
3. For list endpoints, avoid loading relationships entirely; return flat data

---

### C-04: Serial AI API Calls in Matching
**File:** `app/services/matching_service.py`

Matching calls the AI API **sequentially for each candidate** (N candidates = N HTTP calls with 30-60s timeouts). Matching 50 candidates could take 25+ minutes.

**Fix:** Use `asyncio.gather()` with a semaphore for bounded concurrency:
```python
sem = asyncio.Semaphore(5)
tasks = [match_one(sem, candidate, position) for candidate in candidates]
results = await asyncio.gather(*tasks)
```

---

### C-05: Blocking I/O in Async Functions
**File:** `app/services/resume_service.py`

`Path.write_bytes()` and `Path.mkdir()` are **synchronous blocking calls** inside async functions. A 20MB file upload will stall the entire event loop for all concurrent requests.

**Fix:** Use `aiofiles` or run blocking I/O in `asyncio.to_thread()`:
```python
await asyncio.to_thread(file_path.write_bytes, content)
```

---

### C-06: Default Secrets in Configuration
**File:** `app/config.py:54`

```python
JWT_SECRET_KEY: str = "change-me-in-production"
```

Default database password and MinIO credentials are also hardcoded. If `JWT_SECRET_KEY` is not overridden in production, tokens are trivially forgeable.

**Fix:**
1. Remove all default values for secrets
2. Add `@model_validator` that raises if secrets are defaults in non-dev environments
3. Use a separate `.env` file pattern with `.env.example` template

---

### C-07: Missing Database Indexes on Foreign Keys
**Files:** Multiple model files

The following foreign keys lack indexes (causing full table scans on joins and lookups):

| Table | Column | Impact |
|-------|--------|--------|
| `positions` | `created_by` | "My positions" queries |
| `candidates` | `position_id` | Pipeline queries |
| `departments` | `parent_id` | Tree traversal |
| `departments` | `head_user_id` | "My departments" |
| `resumes` | `candidate_id` | Candidate detail page |
| `offers` | `candidate_id` | Candidate offers |
| `offers` | `position_id` | Position offers |
| `interviews` | `candidate_id` | Candidate interviews |
| `interviews` | `position_id` | Position interviews |
| `users` | `email` (individual) | Login queries |

**Fix:** Add Alembic migration with `Index()` declarations on all FK columns.

---

### C-08: No Transaction Management for Writes
**Files:** All service files

Write operations have no explicit transaction boundaries. They rely on the outer session's auto-commit in `get_db()`. Multi-step operations (e.g., create offer + create approvals) are not atomic.

**Fix:** Use `async with session.begin()` for write operations, or ensure `get_db()` provides a proper transactional session.

---

### C-09: `resume.parsed_at` Column Type Bug
**File:** `alembic/versions/05b7e71fa93b_initial_hiremind_schema.py`

`parsed_at` is defined as `String(50)` instead of `DateTime`. This means:
- No date comparison queries possible
- Sorting is lexicographic, not chronological
- Type confusion in Python code

**Fix:** Create a new Alembic migration to `ALTER COLUMN parsed_at TYPE TIMESTAMP USING parsed_at::timestamp`.

---

### C-10: Inconsistent `tenant_id` Types
**File:** `alembic/versions/05b7e71fa93b_initial_hiremind_schema.py`

Some tables use `UUID` for `tenant_id`, others use `String(64)`. No foreign key constraints to `tenants` table exist.

**Fix:** Unify to `UUID` type with FK constraint to `tenants.id`.

---

### C-11: Tests Use SQLite Instead of PostgreSQL
**File:** `tests/conftest.py:61`

```python
"sqlite+aiosqlite:///:memory:"
```

Production uses PostgreSQL with JSONB, UUID, and CASCADE deletes. SQLite does not support these features, meaning tests never validate actual production query behavior.

**Fix:** Use `testcontainers-python` or a shared PostgreSQL test database.

---

### C-12: File Upload Without Size Limit (DoS Vector)
**File:** `app/routers/resumes.py:65`

`file.read()` reads the entire upload into memory with no size check. A malicious user can exhaust server memory.

**Fix:** Add size validation before reading:
```python
content = await file.read()
if len(content) > MAX_UPLOAD_SIZE:
    raise HTTPException(413, "File too large")
```

---

## Major Issues (P1 — High Priority)

### M-01: Experience Matching Permanently Broken
**File:** `app/services/matching_service.py:34-35`

`required_exp_min` is never populated because `position_service` writes to `experience_years_min` instead. Experience matching scores always return base score only.

---

### M-02: Tags Stored as Skills (Data Corruption)
**File:** `app/services/candidate_service.py`

`data.tags` is stored as `profile["skills"]`. Tags like "urgent"/"referral" pollute skill matching.

**Fix:** Store tags in a separate `profile["tags"]` key.

---

### M-03: Missing Optimistic Locking on Candidate Updates
**File:** `app/services/candidate_service.py`

Candidate model has a `version` field for optimistic locking, but the update endpoint doesn't check/increment it. Concurrent updates will silently overwrite each other. Position correctly implements this pattern.

---

### M-04: No Locking on Offer Approval Flow
**File:** `app/services/offer_service.py`

Concurrent approvals can prematurely mark offers as "approved" without proper locking (SELECT FOR UPDATE).

**Fix:** Use `with_for_update()` on offer reads during approval.

---

### M-05: N+1 in Analytics — Department Summary
**File:** `app/services/analytics_service.py`

`get_department_summary()` issues 1 + 2×D queries instead of a single JOIN + GROUP BY.

---

### M-06: JSONB `.contains()` May Not Work for Array Queries
**File:** `app/services/interview_service.py`

`interviewer_ids` is stored as JSONB but queried with `.contains()` which may not correctly match array elements. Consider using PostgreSQL native `ARRAY` type with `ANY()`.

---

### M-07: Business Logic Leaked into Routers
**Files:** `app/routers/departments.py:38-63`, `app/routers/matching.py:35-41`

- Department tree-building logic is fully inline in the router
- Matching router executes raw SQLAlchemy queries directly

**Fix:** Move tree-building to `DepartmentService.build_tree()`. Move position lookup to `PositionService.get_by_id()`.

---

### M-08: AI Client Called Directly from Routers
**Files:** `app/routers/interviews.py:42`, `app/routers/offers.py:39`

AI endpoints bypass the service layer entirely, calling `ai_client` directly from routers with no validation.

**Fix:** Create `AIService.generate_questions()` and `AIService.generate_salary_recommendation()`.

---

### M-09: Raw `dict` Payloads Without Validation
**Files:** `app/routers/interviews.py:29`, `app/routers/offers.py:27`

AI endpoints accept `payload: dict` with no Pydantic validation. Any JSON is forwarded to the AI provider.

**Fix:** Define typed request schemas (e.g., `AIQuestionRequest`, `AISalaryRequest`).

---

### M-10: Fragile Error Routing via String Matching
**Files:** Almost all router files

Error handling checks `str(exception)` for substrings like `"transition"`, `"conflict"`, `"not found"` to decide HTTP status codes. Any message rewording silently breaks the API contract.

**Fix:** Introduce structured exception hierarchy:
```python
class AppError(Exception): ...
class NotFoundError(AppError): ...
class ConflictError(AppError): ...
class StateTransitionError(AppError): ...
```
Register global FastAPI exception handlers.

---

### M-11: RBAC Rules Incomplete
**File:** `app/middleware/rbac.py`

Only 2 endpoint patterns have RBAC rules. The rest default to allow. No method-specific rules (e.g., GET vs DELETE).

---

### M-12: `resume.file_hash` Missing Unique Constraint
**File:** `app/models/resume.py`

No unique constraint on `file_hash` allows duplicate file uploads.

---

### M-13: Dockerfile Security Issues
**File:** `Dockerfile`

1. Single-stage build includes `gcc`, `libpq-dev`, and test deps in production image
2. Container runs as root
3. No `HEALTHCHECK` directive

**Fix:** Multi-stage build, `USER app`, add HEALTHCHECK.

---

### M-14: Audit Log Creates DB Session Per Request
**File:** `app/middleware/audit.py`

Each audit log write creates a new database session. Under high load, this wastes connection pool resources.

**Fix:** Use the request's existing session or batch audit writes.

---

### M-15: `_health_cache` Not Thread-Safe
**File:** `app/decorators/ai_capability.py`

Global `_health_cache` dict has no locking for async concurrent access. Race conditions possible.

---

### M-16: Schemas Missing Enum Validation
**Files:** All schema files

Status, type, and priority fields across all schemas use raw `str` without enum validation. Invalid values are silently accepted.

**Fix:** Define `Literal` or `Enum` types:
```python
class PositionStatus(str, Enum):
    draft = "draft"
    open = "open"
    closed = "closed"
```

---

### M-17: Missing Schema Definitions for Resume
**File:** `app/schemas/resume.py`

No `ResumeCreate` / `ResumeUpdate` schemas. Upload validation is ad-hoc.

---

### M-18: Analytics Endpoints Return Raw Dicts
**File:** `app/routers/analytics.py`

All analytics endpoints return `dict` without `response_model`. No OpenAPI documentation, no runtime validation.

---

### M-19: Pagination Math Duplicated Across 7 Files
**Files:** All router files except analytics

`math.ceil(total / page_size)` is repeated in every list endpoint. Should be extracted to a shared utility.

---

## Minor Issues (P2 — Address in Sprint Backlog)

### m-01 to m-15

| # | Issue | File |
|---|-------|------|
| m-01 | `HireMindModel` base defined but unused | `schemas/__init__.py` |
| m-02 | `to_camel()` function defined but never used | `schemas/__init__.py` |
| m-03 | Inline imports in `main.py` middleware section | `main.py:101-103` |
| m-04 | No request body sanitization in audit log | `middleware/audit.py` |
| m-05 | `group_by` param in analytics accepts any string | `routers/analytics.py:51` |
| m-06 | Bare integer status codes instead of constants | `routers/resumes.py:79,94` |
| m-07 | `StageAdvanceRequest` defined in router, not schema | `routers/candidates.py:25-26` |
| m-08 | `MatchListResponse` hardcodes `pages=1` | `schemas/matching.py` |
| m-09 | `departments.list_departments` re-implements pagination | `routers/departments.py:72-74` |
| m-10 | `cache_ttl` defined but not implemented in AI decorator | `decorators/ai_capability.py` |
| m-11 | No rate limiting on AI capabilities | All AI endpoints |
| m-12 | Missing composite index on `(tenant_id, status)` | `position`, `candidate` models |
| m-13 | `candidates.status` and `stage` not indexed | `candidate` model |
| m-14 | `embedding_id` not indexed for similarity search | `position`, `candidate` models |
| m-15 | No environment-specific config profiles | `config.py` |

---

## Architecture Consistency Assessment

### Positive Patterns

1. **Layered Architecture:** Router → Service → Model is consistently followed (with noted exceptions)
2. **Multi-tenancy:** `TenantMixin` applied to most models with consistent `tenant_id` filtering
3. **Privacy by Design:** Candidate PII encrypted, hashes for deduplication
4. **Optimistic Locking:** `version` field on key models
5. **Audit Trail:** Comprehensive audit logging middleware
6. **Structured Logging:** `structlog` used throughout
7. **Pagination:** Consistent envelope pattern with `PaginationDep`
8. **Naming:** Consistent snake_case, clear class/table names

### Areas for Improvement

1. **Exception Strategy:** Need structured exception hierarchy (see M-10)
2. **Response Standardization:** Some endpoints lack `response_model`
3. **Schema Completeness:** Missing enums, cross-field validations, Create/Update schemas for resume
4. **Test Coverage:** Tests don't validate production database behavior
5. **Observability:** No distributed tracing, no metrics export

---

## Recommended Action Plan

### Phase 1 — Security Hardening (Week 1)
1. Remove auth bypass default (C-01)
2. Add RBAC to all endpoints (C-02)
3. Remove default secrets (C-06)
4. Add file upload size limits (C-12)

### Phase 2 — Performance (Week 2)
1. Fix relationship lazy loading strategy (C-03)
2. Add missing database indexes (C-07)
3. Parallelize AI matching calls (C-04)
4. Fix blocking I/O in resume service (C-05)

### Phase 3 — Data Integrity (Week 3)
1. Fix `parsed_at` column type (C-09)
2. Unify `tenant_id` types (C-10)
3. Add transaction management (C-08)
4. Fix experience matching bug (M-01)
5. Fix tags/skills data corruption (M-02)

### Phase 4 — Architecture Cleanup (Week 4)
1. Introduce structured exceptions (M-10)
2. Move business logic out of routers (M-07, M-08)
3. Add typed schemas for AI endpoints (M-09)
4. Fix Dockerfile (M-13)
5. Switch tests to PostgreSQL (C-11)

---

## Conclusion

The HireMind backend demonstrates solid architectural foundations with a clean layered pattern, multi-tenancy support, and privacy-conscious design. The most urgent work is **security hardening** (auth bypass, RBAC, secrets) followed by **performance** (eager-loading bomb, missing indexes, serial AI calls). The codebase would benefit from a structured exception hierarchy to replace the fragile string-matching error routing pattern.

**Review Conclusion: Critical 12, Major 19, Minor 15 — Total 46 Issues.**
