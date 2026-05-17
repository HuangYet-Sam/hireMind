# HireMind — AI-Native Recruitment System

> Intelligent recruitment management platform built with FastAPI + Vue 3 + PostgreSQL (pgvector).  
> Forked from [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Node 23+](https://img.shields.io/badge/Node-23+-green.svg)](https://nodejs.org)
[![Vue 3.5](https://img.shields.io/badge/Vue-3.5-brightgreen.svg)](https://vuejs.org)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Reverse Proxy (Nginx/Caddy)              │
│                     :80/:443 → SSL Termination                  │
├─────────────────────────┬───────────────────────────────────────┤
│   Vue 3 Frontend        │        FastAPI Backend                │
│   (Nginx serving SPA)   │        (hr-api :8000)                 │
│   /hr/* → HR Pages      │        /api/v1/* → REST API           │
│   /hermes/* → Admin     │        52 endpoints, JWT+RBAC auth    │
├─────────────────────────┴───────────────────────────────────────┤
│                        Service Layer                             │
│   Positions · Candidates · Resumes · Matching · Interviews      │
│   Offers · Analytics · Departments · AI Tasks                   │
├─────────────────────────────────────────────────────────────────┤
│   PostgreSQL 17 (pgvector)  │  Redis 7  │  MinIO (S3 storage)  │
│   Async via SQLAlchemy      │  Caching  │  Resume file storage  │
└─────────────────────────────────────────────────────────────────┘
```

**Tech Stack:**

| Layer | Technology |
|---|---|
| Frontend | Vue 3.5 + Vite 8 + Naive UI + Pinia 3 + Vue Router 4 |
| Backend (HR) | Python 3.12 + FastAPI + SQLAlchemy async + Alembic |
| Backend (Hermes) | Koa 2 + TypeScript (BFF for AI agent admin) |
| Database | PostgreSQL 17 + pgvector (vector search) |
| Cache / Queue | Redis 7 |
| File Storage | MinIO (S3-compatible) |
| Authentication | JWT + RBAC (viewer/recruiter/hr_manager/admin) |
| AI | OpenAI GPT-4o-mini (resume parsing, matching, interview questions) |

---

## Features

- **Position Management** — Create, publish, and track job openings across departments
- **Candidate Pipeline** — Full lifecycle tracking from application to hire with stage management
- **AI Resume Parsing** — Upload PDF/DOCX resumes, automatic AI-powered extraction and scoring
- **Intelligent Matching** — AI-powered candidate-position compatibility scoring with vector search
- **Interview Scheduling** — AI-generated interview questions, scheduling, and feedback collection
- **Offer Management** — Draft, approve, and send offers with AI salary recommendations
- **Analytics Dashboard** — Pipeline funnel, time-to-hire, source effectiveness, department metrics
- **AI Task Center** — Background task management for resume parsing, matching, and reports
- **Multi-tenant** — Full data isolation with tenant-scoped queries
- **RBAC** — Role-based access control with 4 permission levels

---

## Quick Start

### Prerequisites

- Docker Engine 24.0+ with Compose v2
- 8 GB RAM, 50 GB disk
- A domain name pointed to your server (for HTTPS)

### 1. Clone and Configure

```bash
git clone https://github.com/HuangYet-Sam/hireMind.git
cd hireMind
cp .env.example .env.production
```

Edit `.env.production` — at minimum change these required variables:

```bash
# Generate a secure JWT secret
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Set strong passwords
POSTGRES_PASSWORD=<your-secure-password>
MINIO_ROOT_PASSWORD=<your-secure-password>
MINIO_ACCESS_KEY=<your-access-key>
MINIO_SECRET_KEY=<your-secret-key>

# Set your domain
CORS_ORIGINS=["https://your-domain.com"]
```

### 2. Start Services

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Verify

```bash
curl http://localhost/health
# {"status":"ok"}
```

Open `https://your-domain.com` to access the application.

> For detailed deployment instructions including SSL configuration, see [docs/deployment.md](docs/deployment.md).

---

## Development

### Local Development Setup

#### HR Backend (FastAPI)

```bash
cd packages/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

- API docs: `http://localhost:8000/api/docs` (Swagger)
- Tests: `pytest` (104 tests, SQLite in-memory)

#### Frontend (Vue 3)

```bash
npm install
npm run dev
```

- Dev server: `http://localhost:8648`
- Build: `npm run build`

#### Infrastructure Services

```bash
docker compose -f docker-compose.infra.yml up -d
```

This starts PostgreSQL (port 5433), Redis (6379), and MinIO (9000/9001).

### Running Tests

```bash
# Backend tests (104 tests)
cd packages/api && source .venv/bin/activate && pytest -v

# Frontend tests
npm run test
```

### Database Migrations

```bash
cd packages/api
source .venv/bin/activate

# Create migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current state
alembic current
```

> For development conventions, see [docs/dev-spec.md](docs/dev-spec.md) and [CLAUDE.md](CLAUDE.md).

---

## API Overview

**Base URL:** `/api/v1/`  
**Authentication:** JWT Bearer token or API key  
**Documentation:** `http://localhost:8000/api/docs`

| Module | Endpoints | Description |
|---|---|---|
| Positions | 5 | CRUD for job openings |
| Candidates | 6 | CRUD + stage pipeline advancement |
| Resumes | 5 | Upload, parse, manage resume files |
| Matching | 3 | AI-powered candidate-position matching |
| Interviews | 7 | Scheduling, questions, feedback |
| Offers | 8 | Draft, approve, send, withdraw |
| Analytics | 5 | Dashboard, pipeline, time-to-hire metrics |
| Departments | 6 | Organization hierarchy management |
| AI Tasks | 5 | Background task lifecycle management |
| **Total** | **52** | |

See [API_ENDPOINTS.md](API_ENDPOINTS.md) for complete endpoint documentation.

---

## Documentation

| Document | Description |
|---|---|
| [docs/deployment.md](docs/deployment.md) | Production deployment guide |
| [docs/operations.md](docs/operations.md) | Operations and maintenance manual |
| [API_ENDPOINTS.md](API_ENDPOINTS.md) | Complete API reference (52 endpoints) |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [docs/docker.md](docs/docker.md) | Docker Compose guide (Hermes services) |
| [docs/README.md](docs/README.md) | Full documentation index |
| [prd/HireMind-PRD-V3.6.md](prd/HireMind-PRD-V3.6.md) | Product requirements document |

---

## Project Structure

```
hireMind/
├── packages/
│   ├── client/src/         # Vue 3 frontend
│   │   ├── views/hr/       # HR recruitment pages (10 views)
│   │   ├── views/hermes/   # Hermes admin pages (18 views)
│   │   ├── api/hr/         # HR API client modules
│   │   ├── stores/hr/      # HR Pinia stores
│   │   └── components/hr/  # HR UI components
│   ├── server/src/         # Koa BFF (Hermes admin backend)
│   └── api/                # FastAPI HR backend
│       ├── app/            # Application code
│       │   ├── routers/    # Route handlers
│       │   ├── services/   # Business logic
│       │   ├── models/     # SQLAlchemy models
│       │   ├── schemas/    # Pydantic schemas
│       │   ├── middleware/  # Auth, RBAC, Audit
│       │   └── config.py   # Settings (env-based)
│       ├── alembic/        # Database migrations
│       ├── tests/          # pytest (104 tests)
│       └── Dockerfile
├── docs/                   # Documentation
├── prd/                    # Product requirements
├── scripts/                # Development/deployment scripts
├── docker-compose.infra.yml  # Infrastructure services
└── docker-compose.yml      # Hermes web-ui services
```

---

## License

MIT (inherited from hermes-web-ui)
