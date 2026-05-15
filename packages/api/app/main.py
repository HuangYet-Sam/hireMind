"""
HireMind AI Recruitment System - FastAPI Backend Entry Point.

Launch with: uvicorn app.main:app --reload  (from packages/api/)
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    analytics,
    candidates,
    departments,
    interviews,
    matching,
    offers,
    positions,
    resumes,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────
    import logging

    from app.dependencies import _engine

    logger = logging.getLogger("hiremind")
    logger.info("🚀 HireMind API starting...")
    logger.info("📂 Creating database tables (if not exist)...")

    async with _engine.begin() as conn:
        from app.models.base import Base

        await conn.run_sync(Base.metadata.create_all)

    # Seed default tenant + user
    from app.dependencies import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from app.models.tenant import Tenant
        from app.models.user import User

        result = await session.execute(
            select(Tenant).where(Tenant.name == "默认租户")
        )
        if not result.scalar_one_or_none():
            tenant = Tenant(name="默认租户", plan="pro", status="active")
            session.add(tenant)
            await session.flush()

            user = User(
                tenant_id=tenant.id,
                email="admin@hiremind.local",
                name_encrypted="Admin",
                role="hr_admin",
            )
            session.add(user)
            await session.commit()
            logger.info("🌱 Seeded default tenant and admin user.")

    logger.info("✅ Database ready.")
    logger.info("🌐 CORS allowed origins: %s", settings.CORS_ORIGINS)

    yield  # ── Application runs here ──────────────────────────

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("🛑 HireMind API shutting down...")
    await _engine.dispose()
    logger.info("✅ Shutdown complete.")


# ── FastAPI App ────────────────────────────────────────────────
app = FastAPI(
    title="HireMind AI Recruitment System",
    description="Intelligent recruitment platform powered by AI",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS Middleware ────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-Id", "X-API-Key"],
)

# ── Custom Middleware (order matters: outermost first) ─────────
from app.middleware.audit import AuditLogMiddleware  # noqa: E402
from app.middleware.auth import AuthMiddleware  # noqa: E402
from app.middleware.rbac import RBACMiddleware  # noqa: E402

app.add_middleware(AuditLogMiddleware)
app.add_middleware(RBACMiddleware)
app.add_middleware(AuthMiddleware)

# ── Route Registration ────────────────────────────────────────
app.include_router(positions.router, prefix="/api/v1/positions", tags=["Positions"])
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["Candidates"])
app.include_router(resumes.router, prefix="/api/v1/resumes", tags=["Resumes"])
app.include_router(matching.router, prefix="/api/v1/matching", tags=["Matching"])
app.include_router(interviews.router, prefix="/api/v1/interviews", tags=["Interviews"])
app.include_router(offers.router, prefix="/api/v1/offers", tags=["Offers"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(departments.router, prefix="/api/v1/departments", tags=["Departments"])


# ── Root & Health Check ────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    """Root endpoint returning API info."""
    return {"service": "hiremind-api", "version": "0.1.0"}


@app.get("/health", tags=["System"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "hiremind-api", "version": "0.1.0"}
