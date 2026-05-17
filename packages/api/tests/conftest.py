"""
HireMind Backend Test Configuration

Provides async fixtures for SQLite in-memory testing with PG type compatibility.
"""

import sqlite3
import uuid as _uuid
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from app import dependencies
from app.main import app
from app.models.base import Base
from app.models.department import Department
from app.models.position import Position
from app.models.tenant import Tenant

# Register SQLite adapter so uuid.UUID objects are stored as strings
sqlite3.register_adapter(_uuid.UUID, lambda u: str(u))

# Make PG UUID type work with SQLite: convert string results back to UUID objects
_orig_rp = PG_UUID.result_processor


def _patched_rp(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None and isinstance(value, (str, bytes)):
                v = value.decode() if isinstance(value, bytes) else value
                try:
                    return _uuid.UUID(v)
                except (ValueError, AttributeError):
                    return v
            return value
        return process
    return _orig_rp(self, dialect, coltype)


PG_UUID.result_processor = _patched_rp


# ── PG → SQLite Type Compilation ──────────────────────────────────────

@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Fixed UUIDs for consistent test data
TEST_TENANT_UUID = uuid4()
TEST_TENANT_ID_STR = str(TEST_TENANT_UUID)


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Async HTTP client with DB and auth dependency overrides."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return dependencies.CurrentUser(
            user_id="test-user-id",
            tenant_id=TEST_TENANT_ID_STR,
            role="admin",
        )

    app.dependency_overrides[dependencies.get_db] = override_get_db
    app.dependency_overrides[dependencies.get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "test-key", "X-Tenant-Id": TEST_TENANT_ID_STR},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_tenant(db_session: AsyncSession):
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == TEST_TENANT_UUID)
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(
            id=TEST_TENANT_UUID,
            name="Test Tenant",
            plan="pro",
            status="active",
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture(scope="function")
async def test_department(db_session: AsyncSession, test_tenant):
    dept = Department(
        name="Engineering",
        code="ENG",
        tenant_id=str(test_tenant.id),
        status="active",
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept


@pytest_asyncio.fixture(scope="function")
async def test_position(db_session: AsyncSession, test_tenant, test_department):
    position = Position(
        title="Senior Software Engineer",
        department_id=test_department.id,
        tenant_id=str(test_tenant.id),
        status="draft",
        headcount=1,
        employment_type="full_time",
    )
    db_session.add(position)
    await db_session.commit()
    await db_session.refresh(position)
    return position
