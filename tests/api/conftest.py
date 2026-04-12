"""
Shared fixtures for API integration tests.
Uses a real in-memory SQLite (via aiosqlite) database so tests are fully isolated
and do NOT require a running Postgres instance.

Run from the repo root:
    cd backend && pytest ../tests/api/ -v
"""
import sys
import os
# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db

# Use SQLite in-memory for tests (fast, no Postgres needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    """Create all tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """HTTP client wired to the FastAPI app with the test DB."""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register + login a test user and return Bearer headers."""
    await client.post(
        "/api/users/register",
        json={"email": "user@test.com", "password": "password123", "name": "Test User"},
    )
    resp = await client.post(
        "/api/users/login",
        json={"email": "user@test.com", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_auth_headers(client: AsyncClient) -> dict:
    """Register + login a second user (for permission boundary tests)."""
    await client.post(
        "/api/users/register",
        json={"email": "other@test.com", "password": "password123", "name": "Other User"},
    )
    resp = await client.post(
        "/api/users/login",
        json={"email": "other@test.com", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
