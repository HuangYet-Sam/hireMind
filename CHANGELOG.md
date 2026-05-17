# Changelog

All notable changes to the **HireMind AI Recruitment System** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2025-05-17

### Backend

#### Security Hardening
- **RBAC enforcement**: Added `require_role()` dependency to all write operations (POST/PATCH/DELETE) across candidates, positions, interviews, and offers routers. Write access now restricted to `recruiter`, `hr_manager`, and `admin` roles.
- **Offer approval**: Requires `hr_manager` or `admin` role (`_HrManagerOrAbove`).
- **Auth middleware**: Removed `dev_user` fallback from auth middleware. All requests must carry a valid JWT / API key — no more automatic dev impersonation.

#### AI Tasks API (New)
- Added **AiTask** model with full lifecycle management.
- New router `ai_tasks` mounted at `/api/v1/ai-tasks` with 5 endpoints:
  - `POST /` — Create a new AI task
  - `GET /` — List tasks (paginated, filterable by status)
  - `GET /{task_id}` — Retrieve a single task by ID
  - `POST /{task_id}/cancel` — Cancel a running/pending task
  - `POST /{task_id}/retry` — Retry a failed task

#### Matching Service
- **Parallelized AI scoring**: `matching_service` now uses `asyncio.gather()` to run AI evaluation calls concurrently, significantly reducing matching latency for large candidate sets.

#### Tests
- Fixed test authentication setup to work with the new auth middleware (no dev fallback).

> Commit: `cd6f14f` — fix(backend): security hardening, RBAC, matching parallelization, Tasks API, test auth fix

### Frontend

- **Matching params**: Fixed request parameter mapping in matching API calls.
- **Analytics unwrap**: Fixed response unwrapping in analytics dashboard data fetching.
- **Offers reject**: Fixed offer rejection flow in the UI.

> Commit: `50e2abc` — fix(frontend): matching params, analytics unwrap, offers reject

---

## [0.1.0] - 2025-05-01

### Added
- Initial release of HireMind AI Recruitment System.
- Core modules: Positions, Candidates, Resumes, Interviews, Offers, Departments, Analytics, Matching.
- FastAPI backend with SQLAlchemy async + PostgreSQL.
- Vue 3 + Naive UI frontend with Pinia state management.
- MinIO object storage for resume files.
- Redis for caching and task queues.
- Alembic database migrations.
