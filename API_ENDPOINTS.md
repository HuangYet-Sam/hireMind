# HireMind API Endpoints Reference

> **Base URL**: `http://localhost:8000`
> **OpenAPI Docs**: `http://localhost:8000/api/docs` (Swagger) · `http://localhost:8000/api/redoc` (ReDoc)
> **Authentication**: Most endpoints require a valid JWT or API key via `Authorization: Bearer <token>` header (enforced by `AuthMiddleware`). Tenancy is resolved via `X-Tenant-Id` header or JWT claims.

---

## Table of Contents

- [System](#system)
- [Positions](#positions)
- [Candidates](#candidates)
- [Resumes](#resumes)
- [Matching](#matching)
- [Interviews](#interviews)
- [Offers](#offers)
- [Analytics](#analytics)
- [Departments](#departments)
- [AI Tasks](#ai-tasks)

---

## System

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/` | Root endpoint — returns API service info and version | None |
| GET | `/health` | Health check — returns `{ status: "ok" }` | None |

---

## Positions

**Prefix**: `/api/v1/positions` · **Tag**: `Positions`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| GET | `/` | List positions (paginated). Filters: `department_id`, `status`, `keyword` | Required | Any authenticated user |
| POST | `/` | Create a new position | Required | `recruiter` / `hr_manager` / `admin` |
| GET | `/{position_id}` | Get a single position by ID | Required | Any authenticated user |
| PATCH | `/{position_id}` | Update a position | Required | `recruiter` / `hr_manager` / `admin` |
| DELETE | `/{position_id}` | Soft-delete a position | Required | `recruiter` / `hr_manager` / `admin` |

---

## Candidates

**Prefix**: `/api/v1/candidates` · **Tag**: `Candidates`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| GET | `/` | List candidates (paginated). Filters: `position_id`, `status`, `stage`, `keyword` | Required | Any authenticated user |
| POST | `/` | Create a new candidate | Required | `recruiter` / `hr_manager` / `admin` |
| GET | `/{candidate_id}` | Get a single candidate by ID | Required | Any authenticated user |
| PATCH | `/{candidate_id}` | Update a candidate | Required | `recruiter` / `hr_manager` / `admin` |
| DELETE | `/{candidate_id}` | Soft-delete a candidate | Required | `recruiter` / `hr_manager` / `admin` |
| POST | `/{candidate_id}/stage` | Advance candidate pipeline stage | Required | `recruiter` / `hr_manager` / `admin` |

---

## Resumes

**Prefix**: `/api/v1/resumes` · **Tag**: `Resumes`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| GET | `/` | List resumes (paginated). Filters: `candidate_id`, `status` | Required | Any authenticated user |
| POST | `/upload` | Upload a resume file (PDF/DOCX). Form-data: `file`, `candidate_id?`, `position_id?`, `source?` | Required | Any authenticated user |
| GET | `/{resume_id}` | Get a single resume by ID | Required | Any authenticated user |
| POST | `/{resume_id}/parse` | Trigger AI-powered resume parsing (or re-parse) | Required | Any authenticated user |
| DELETE | `/{resume_id}` | Delete a resume and its stored file | Required | Any authenticated user |

---

## Matching

**Prefix**: `/api/v1/matching` · **Tag**: `Matching`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| POST | `/position/{position_id}/candidates` | AI-powered candidate matching for a position. Query params: `top_k`, `min_score` | Required | Any authenticated user |
| POST | `/candidate/{candidate_id}/positions` | AI-powered position matching for a candidate. Query params: `top_k`, `min_score` | Required | Any authenticated user |
| GET | `/position/{position_id}/result` | Get latest match results for a position | Required | Any authenticated user |

---

## Interviews

**Prefix**: `/api/v1/interviews` · **Tag**: `Interviews`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| POST | `/ai/questions` | Generate AI interview questions for a position-candidate pair | Required | Any authenticated user |
| GET | `/` | List interviews (paginated). Filters: `candidate_id`, `position_id`, `interviewer_id`, `date_from`, `date_to` | Required | Any authenticated user |
| POST | `/` | Schedule a new interview | Required | `recruiter` / `hr_manager` / `admin` |
| GET | `/{interview_id}` | Get a single interview by ID | Required | Any authenticated user |
| PATCH | `/{interview_id}` | Update an interview | Required | `recruiter` / `hr_manager` / `admin` |
| DELETE | `/{interview_id}` | Cancel an interview. Query param: `reason?` | Required | `recruiter` / `hr_manager` / `admin` |
| POST | `/{interview_id}/feedback` | Submit interview feedback and rating | Required | `recruiter` / `hr_manager` / `admin` |

---

## Offers

**Prefix**: `/api/v1/offers` · **Tag**: `Offers`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| POST | `/ai/salary-recommendation` | Generate AI salary recommendation for an offer | Required | Any authenticated user |
| GET | `/` | List offers (paginated). Filters: `candidate_id`, `position_id`, `status` | Required | Any authenticated user |
| POST | `/` | Create a new offer | Required | `recruiter` / `hr_manager` / `admin` |
| GET | `/{offer_id}` | Get a single offer by ID | Required | Any authenticated user |
| PATCH | `/{offer_id}` | Update an offer (draft only) | Required | `recruiter` / `hr_manager` / `admin` |
| POST | `/{offer_id}/approve` | Approve an offer | Required | `hr_manager` / `admin` |
| POST | `/{offer_id}/send` | Send an offer to candidate | Required | `recruiter` / `hr_manager` / `admin` |
| DELETE | `/{offer_id}` | Withdraw an offer. Query param: `reason?` | Required | Any authenticated user |

---

## Analytics

**Prefix**: `/api/v1/analytics` · **Tag**: `Analytics`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| GET | `/dashboard` | Recruitment dashboard aggregates. Query param: `department_id?` | Required | Any authenticated user |
| GET | `/pipeline` | Hiring pipeline funnel (applied → screened → interviewed → offered → hired). Params: `date_from?`, `date_to?` | Required | Any authenticated user |
| GET | `/time-to-hire` | Average time-to-hire metrics. Params: `date_from?`, `date_to?`, `group_by` (day/week/month) | Required | Any authenticated user |
| GET | `/source-effectiveness` | Candidate source effectiveness comparison | Required | Any authenticated user |
| GET | `/department-summary` | Per-department recruitment metrics | Required | Any authenticated user |

---

## Departments

**Prefix**: `/api/v1/departments` · **Tag**: `Departments`

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| GET | `/tree` | Get full department hierarchy tree | Required | Any authenticated user |
| GET | `/` | List departments (paginated). Filter: `parent_id?` | Required | Any authenticated user |
| POST | `/` | Create a new department | Required | Any authenticated user |
| GET | `/{department_id}` | Get a single department by ID | Required | Any authenticated user |
| PATCH | `/{department_id}` | Update a department | Required | Any authenticated user |
| DELETE | `/{department_id}` | Soft-delete a department | Required | Any authenticated user |

---

## AI Tasks

**Prefix**: `/api/v1/ai-tasks` · **Tag**: `AI Tasks`

> 🆕 **New in v0.2.0** — Background AI task lifecycle management.

| Method | Path | Description | Auth | RBAC |
|--------|------|-------------|------|------|
| POST | `/` | Create a new AI task | Required | Any authenticated user |
| GET | `/` | List AI tasks (paginated). Filter: `status` (pending/running/completed/failed/cancelled) | Required | Any authenticated user |
| GET | `/{task_id}` | Get a single AI task by ID | Required | Any authenticated user |
| POST | `/{task_id}/cancel` | Cancel a pending or running task | Required | Any authenticated user |
| POST | `/{task_id}/retry` | Retry a failed task | Required | Any authenticated user |

---

## Summary Statistics

| Module | Endpoints | Auth Required | RBAC Protected |
|--------|-----------|---------------|----------------|
| System | 2 | No | — |
| Positions | 5 | Yes | 3 (POST/PATCH/DELETE) |
| Candidates | 6 | Yes | 4 (POST/PATCH/DELETE/stage) |
| Resumes | 5 | Yes | — |
| Matching | 3 | Yes | — |
| Interviews | 7 | Yes | 5 (POST/PATCH/DELETE/feedback) |
| Offers | 8 | Yes | 4 (create/update/approve/send) |
| Analytics | 5 | Yes | — |
| Departments | 6 | Yes | — |
| AI Tasks | 5 | Yes | — |
| **Total** | **52** | | |

---

## Common Patterns

### Authentication

All `/api/v1/*` endpoints require a valid `Authorization: Bearer <token>` header, enforced by `AuthMiddleware`. The middleware validates JWT tokens or API keys and populates `current_user` with `tenant_id`, `user_id`, and `role`.

### Tenant Isolation

All data queries are scoped by `tenant_id` extracted from the authenticated user. Cross-tenant access is not possible.

### Pagination

List endpoints accept `page` (default 1) and `page_size` (default 20, max 100) query parameters and return:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

### Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Bad Request — invalid input |
| 401 | Unauthorized — missing or invalid auth |
| 403 | Forbidden — insufficient role |
| 404 | Not Found — resource doesn't exist |
| 409 | Conflict — state transition error, duplicate |
| 422 | Validation Error — Pydantic schema mismatch |
| 503 | AI Service Unavailable — external AI dependency down |

---

*Last updated: 2025-05-17 · Generated from router source files in `packages/api/app/routers/`*
