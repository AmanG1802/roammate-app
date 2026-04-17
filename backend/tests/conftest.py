"""
Shared fixtures for all backend tests (api/, services/, core/, cross/, schemas/).
Uses an in-memory SQLite database (aiosqlite) so tests run without Postgres.

Run from backend/:
    pytest tests/ -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession,
    expire_on_commit=False, autoflush=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    """Create all tables before each test, drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Direct DB session for service/unit tests that don't need HTTP."""
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _register_and_login(client: AsyncClient, email: str, name: str, password: str = "password123") -> dict:
    await client.post(
        "/api/users/register",
        json={"email": email, "password": password, "name": name},
    )
    resp = await client.post(
        "/api/users/login",
        json={"email": email, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register + login the primary test user (Alice)."""
    return await _register_and_login(client, "alice@test.com", "Alice Smith")


@pytest_asyncio.fixture
async def second_auth_headers(client: AsyncClient) -> dict:
    """Register + login a second user (Bob) for permission tests."""
    return await _register_and_login(client, "bob@test.com", "Bob Jones")


@pytest_asyncio.fixture
async def third_auth_headers(client: AsyncClient) -> dict:
    """Register + login a third user (Carol) for outsider-access tests."""
    return await _register_and_login(client, "carol@test.com", "Carol Doe")


# ── Convenience helpers (not fixtures) ───────────────────────────────────────

async def create_trip(client: AsyncClient, headers: dict, **payload) -> dict:
    payload.setdefault("name", "Test Trip")
    resp = await client.post("/api/trips/", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def invite_and_accept(
    client: AsyncClient,
    admin_headers: dict,
    invitee_headers: dict,
    trip_id: int,
    email: str,
    role: str = "view_only",
) -> dict:
    """Admin invites invitee; invitee accepts. Returns the accepted membership row."""
    resp = await client.post(
        f"/api/trips/{trip_id}/invite",
        json={"email": email, "role": role},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    member_id = resp.json()["id"]
    resp = await client.post(
        f"/api/trips/invitations/{member_id}/accept",
        headers=invitee_headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
