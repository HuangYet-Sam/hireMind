# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**HireMind** is an AI-native recruitment system, forked from [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui). It combines the original Hermes Agent admin dashboard with a new HireMind HR recruitment platform.

Two subsystems share the same Vue frontend:

| Subsystem | Routes | Backend | Purpose |
|-----------|--------|---------|---------|
| **Hermes Admin** | `/hermes/*` (16 pages) | Koa BFF on `:8648` | AI agent management, chat, models, channels, jobs |
| **HireMind HR** | `/hr/*` (10 pages) | FastAPI on `:8000` | Positions, candidates, resumes, matching, interviews, offers |

**Architecture overview:**
```
┌─ Vue 3 Frontend (:8648 Vite dev) ─────────────────────────┐
│  /hermes/* → Koa BFF (:8648) → Hermes Agent (:8642)       │
│  /hr/*     → FastAPI (:8000) → PostgreSQL + MinIO + Redis │
└────────────────────────────────────────────────────────────┘
```

**Tech stack:**
- **Frontend:** Vue 3 (Composition API, `<script setup lang="ts">`), Naive UI, Pinia, vue-router (hash history), vue-i18n, SCSS, Vite
- **Hermes Backend:** Koa 2, @koa/router v15+, Socket.IO, node-pty, SQLite, reverse proxy to Hermes gateway
- **HR Backend:** Python 3.12+, FastAPI, SQLAlchemy async (PostgreSQL), Alembic, Redis, MinIO, PyJWT
- **Language:** TypeScript (strict, both client/server) + Python (HR backend)
- **Node:** >= 23.0.0

---

## Development Commands

### Hermes (Node.js)

```bash
npm run dev           # Start Koa server + Vite client concurrently
npm run dev:client    # Vite dev server only (proxies API to Koa backend)
npm run dev:server    # nodemon + ts-node for Koa server only
npm run build         # vue-tsc → Vite build → tsc server check → esbuild server bundle
npm run test          # vitest run
npm run test:watch    # vitest watch
npx vitest run tests/server/sessions-db.test.ts           # Single test file
npx vitest run tests/server/sessions-db.test.ts -t "foo"  # Single test case
```

- **Dev port:** 8648 (Vite proxies `/api`, `/v1`, `/health`, `/upload`, `/webhook`, `/socket.io` to Koa)
- **Prerequisite:** `hermes` CLI on `$PATH` (Koa wraps it via `child_process.execFile`)

### HR Backend (Python)

```bash
cd packages/api
python -m venv .venv && source .venv/bin/activate  # Create/activate venv
pip install -r requirements.txt
alembic upgrade head          # Run database migrations
uvicorn app.main:app --reload # Start FastAPI dev server (port 8000)
pytest                        # Run Python tests
pytest tests/test_health.py   # Single test file
```

- **Dev port:** 8000 (FastAPI)
- **Docs:** `http://localhost:8000/api/docs` (Swagger), `/api/redoc` (ReDoc)
- **Prerequisites:** PostgreSQL, Redis, MinIO running locally

---

## Architecture

### Directory Layout

```
packages/
├── client/src/            # Vue 3 frontend (shared for both subsystems)
│   ├── api/
│   │   ├── client.ts      # Shared base: Hermes BFF fetch wrapper
│   │   ├── hr/client.ts   # HR API client: direct connection to FastAPI :8000
│   │   ├── hermes/        # Hermes API modules (~25 files)
│   │   └── hr/            # HR API modules (~10 files)
│   ├── components/
│   │   ├── layout/        # Shared: AppSidebar, ModelSelector, HrLayout
│   │   ├── hermes/        # Hermes components (~12 feature dirs)
│   │   └── hr/            # HR components: CandidateCard, MatchScore, ResumeViewer, etc.
│   ├── composables/       # Shared composables (useKeyboard, useTheme, useSmartConfig, etc.)
│   ├── i18n/locales/      # 8 locales: en, zh, de, es, fr, ja, ko, pt
│   ├── router/index.ts    # All routes for both subsystems
│   ├── stores/
│   │   ├── hermes/        # Hermes Pinia stores (~12)
│   │   └── hr/            # HR Pinia stores (~8)
│   ├── styles/            # SCSS: variables, global, code-block, theme
│   └── views/
│       ├── LoginView.vue  # Shared login page
│       ├── hermes/        # Hermes pages (~18 views)
│       └── hr/            # HR pages (~10 views)
├── server/src/            # Koa BFF server (Hermes admin)
│   ├── controllers/hermes/  # ~23 controller files
│   ├── db/hermes/           # SQLite layer (schemas, session-store, usage-store, etc.)
│   ├── lib/                 # Shared utils (llm-json, context-compressor, llm-prompt)
│   ├── routes/hermes/       # ~31 route files (thin wrappers)
│   └── services/hermes/     # ~25 service files + context-engine/ + group-chat/
├── api/                   # Python FastAPI backend (HR recruitment)
│   ├── app/
│   │   ├── main.py        # FastAPI entry, lifespan, middleware, router registration
│   │   ├── config.py      # Pydantic Settings (env-based)
│   │   ├── dependencies.py # DB session, pagination, auth stubs
│   │   ├── decorators/ai_capability.py  # @AiCapability decorator for AI-fn endpoints
│   │   ├── middleware/     # auth.py, rbac.py, audit.py
│   │   ├── models/        # SQLAlchemy models (candidate, position, interview, offer, resume, department)
│   │   ├── routers/       # FastAPI route handlers (~8 routers)
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   └── services/      # Business logic (~8 services)
│   ├── alembic/           # Database migrations
│   ├── tests/             # pytest tests
│   └── Dockerfile
docs/                      # Design docs, architecture, API specs, PRD references
prd/                       # Product requirements (HireMind-PRD-V3.5.md, V3.6.md)
```

### Frontend Routing

Router in `packages/client/src/router/index.ts` defines both subsystems:

- **Hermes routes** — flat paths: `/hermes/chat`, `/hermes/jobs`, `/hermes/models`, etc.
- **HR routes** — nested under `HrLayout.vue`: `/hr/dashboard`, `/hr/positions`, `/hr/candidates`, `/hr/matching`, `/hr/interviews`, `/hr/offers`, `/hr/analytics`, `/hr/tasks`, `/hr/org-chart`

Auth guard: `router.beforeEach` redirects unauthenticated users to `/` (login). Public routes use `meta: { public: true }`.

### Two API Clients

The frontend has **two separate API clients**:

1. **Hermes BFF** (`api/client.ts`) — `request<T>()` fetch wrapper to Koa `:8648`. Auto `Authorization: Bearer` header, 401 redirect to login.
2. **HR API** (`api/hr/client.ts`) — `hrGet/hrPost/hrPut/hrPatch/hrDelete` helpers connecting **directly** to FastAPI `:8000/api/v1`. Uses `hermes_api_key` from localStorage and `X-Tenant-Id` header.

### Hermes Backend Request Flow

1. **Public routes** (no auth): health, webhook, auth
2. **Auth middleware** (`requireAuth`)
3. **Protected routes**: Koa controllers → services → Hermes CLI or SQLite
4. **Proxy catch-all**: unmatched `/api/hermes/*` → upstream Hermes gateway

**Critical:** Custom endpoints must be registered in `routes/index.ts` **before** `proxyRoutes`.

### Hermes Real-Time

Two Socket.IO namespaces on the Koa HTTP server:
- **`/chat-run`** — Streaming chat (Socket.IO rooms by session_id, resume on reconnect)
- **`/` (group-chat)** — Multi-agent group chat rooms

Terminal uses raw WebSocket at `/api/hermes/terminal` with `node-pty`.

### Hermes Database (SQLite)

Initialized on startup via `initAllStores()`. Schema in `db/hermes/schemas.ts`. Key stores: session-store, sessions-db, usage-store, kanban-db, conversations-db.

### HR Backend Architecture (FastAPI)

Follows layered pattern: **Router → Service → Model**:
- **Routers** (`app/routers/`) — endpoint definitions, delegate to services
- **Services** (`app/services/`) — business logic (many TODO stubs for Hermes Agent AI integration)
- **Models** (`app/models/`) — SQLAlchemy ORM models
- **Schemas** (`app/schemas/`) — Pydantic validation schemas
- **Dependencies** (`app/dependencies.py`) — async DB session (`get_db`), pagination (`PaginationParams`), auth stubs (`get_current_user`)

Middleware stack (outermost first): `AuditLogMiddleware` → `RBACMiddleware` → `AuthMiddleware`.

**`@AiCapability` decorator** (`app/decorators/ai_capability.py`) — marks endpoints that require AI capabilities from Hermes Agent. Supports fallback functions and timeout.

### HR Data Layer

- **PostgreSQL** (async via asyncpg + SQLAlchemy) — core business data
- **Redis** — caching and sessions
- **MinIO** — resume file storage
- **Alembic** — database migrations

---

## Naming Conventions

### Multi-Domain Namespacing

All domain-specific code uses directory-based namespacing:

| Layer | Shared | Hermes | HR |
|-------|--------|--------|----|
| API | `api/client.ts` | `api/hermes/*.ts` | `api/hr/*.ts` |
| Components | `components/layout/` | `components/hermes/` | `components/hr/` |
| Views | `views/LoginView.vue` | `views/hermes/` | `views/hr/` |
| Stores | — | `stores/hermes/` | `stores/hr/` |
| Controllers | `controllers/*.ts` | `controllers/hermes/` | Python routers |
| Routes | `routes/*.ts` | `routes/hermes/` | Python routers |
| Services | `services/*.ts` | `services/hermes/` | Python services |
| Route names | `login` | `hermes.{page}` | `hr.{page}` |
| API paths | `/health` | `/api/hermes/*` | `/api/v1/{resource}` |

### Route Naming

- **Hermes:** `hermes.chat`, `hermes.jobs`, `hermes.kanban` → `/hermes/{page}`
- **HR:** `hr.dashboard`, `hr.positions`, `hr.candidates` → `/hr/{page}` (nested under HrLayout)

---

## Frontend Conventions

### Vue Components

All use `<script setup lang="ts">` with Composition API:
- Import Naive UI directly from `naive-ui`
- `useMessage()` for toast, `useI18n()` for translations (`t('key.path')`)
- Scoped SCSS with `@use '@/styles/variables' as *`

### Pinia Stores

Setup store syntax (function passed to `defineStore`). Stores in `stores/hermes/` and `stores/hr/`.

### i18n

8 locales in `i18n/locales/`. Flat nested objects. Add new strings to **all** locale files.

### SCSS

- "Pure Ink" theme (monochrome), no color accent
- Mobile breakpoint: `$breakpoint-mobile: 768px`
- Always `<style scoped lang="scss">`

---

## Hermes Backend Conventions

### Routes + Controllers + Services

- **Routes** (`routes/`) — thin URL-to-handler, delegate to controllers
- **Controllers** (`controllers/`) — request handling
- **Services** (`services/`) — reusable logic, Hermes CLI wrappers
- **DB stores** (`db/`) — SQLite CRUD

### @koa/router v15 (path-to-regexp v8)

- `:id` for single segment, `{*path}` for wildcard
- No regex groups `(.*)`, no modifiers `:id+`/`:id*`

### Reverse Proxy

`/api/hermes/*` → upstream gateway (`http://127.0.0.1:8642`). Rewrites in `proxy-handler.ts`:
- `/api/hermes/v1/*` → `/v1/*`
- `/api/hermes/*` → `/api/*`

---

## HR Backend Conventions (Python/FastAPI)

### Layered Pattern

Router → Service → Model. Schemas for request/response validation.

### Configuration

Pydantic Settings via `app/config.py`. All config from env vars or `.env` file. Key env vars in `packages/api/.env.example`.

### Database

SQLAlchemy async engine + session factory in `app/dependencies.py`. Auto `create_all` on startup. Alembic for migrations.

---

## Build System (Hermes)

- **Vite** frontend: root `packages/client`, output `dist/client`
- **esbuild** server: `scripts/build-server.mjs`, output `dist/server`
- **tsc** type-check: `vue-tsc -b` (client) + `tsc --noEmit` (server)
- Path alias: `@` → `packages/client/src`

---

## Testing

### Hermes (Vitest)

```bash
npm run test          # All tests
npx vitest run tests/server/sessions-db.test.ts  # Single file
```

Test files in `tests/client/`, `tests/server/`, `tests/shared/`.

### HR (pytest)

```bash
cd packages/api && pytest
```

---

## Environment Variables

### Hermes (Koa)

| Variable | Description |
|---|---|
| `AUTH_DISABLED` | `1` to disable auth |
| `AUTH_TOKEN` | Custom token |
| `PORT` | Koa port (default `8648`) |
| `UPSTREAM` | Hermes gateway URL (default `http://127.0.0.1:8642`) |
| `PROFILE` | Active profile (default `default`) |

### HR (FastAPI)

See `packages/api/.env.example`. Key vars: `DATABASE_URL`, `REDIS_URL`, `MINIO_*`, `JWT_SECRET_KEY`, `HERMES_AGENT_URL`.

---

## Common Tasks

### Add a new HR page

1. Create view in `packages/client/src/views/hr/MyView.vue`
2. Add route in `router/index.ts` under the HR children array — name `hr.myPage`, path `my-page`
3. Add sidebar entry in the HR layout or AppSidebar
4. Add i18n keys to all locale files

### Add a new HR API endpoint

1. Add SQLAlchemy model in `packages/api/app/models/`
2. Add Pydantic schemas in `packages/api/app/schemas/`
3. Add service in `packages/api/app/services/`
4. Add router in `packages/api/app/routers/`
5. Register router in `packages/api/app/main.py`
6. Add frontend API functions in `packages/client/src/api/hr/`

### Add a new Hermes page

1. Create view in `packages/client/src/views/hermes/MyView.vue`
2. Add route with name `hermes.myPage`, path `/hermes/my-page`
3. Register in `routes/index.ts` **before** `proxyRoutes`
4. Add controller → route → service layers as needed

### Add a new agent/module

Follow the `hr/` namespacing pattern: create `api/{module}/`, `components/{module}/`, `views/{module}/`, `stores/{module}/` with corresponding backend.

---

## Documentation

- `docs/` — Architecture, API specs, feature docs, audit reports, test strategy
- `prd/` — Product requirements (HireMind-PRD-V3.5.md, V3.6.md) and audit reports
- `docs/README.md` — Documentation index
