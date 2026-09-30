"""API integration tests against in-memory SQLite."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from models.db import Base
from models.database import get_db
from api.main import app


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ingest_and_list(client):
    sid = str(uuid.uuid4())
    r = await client.post(
        "/ingest/events",
        json={
            "session_id": sid,
            "service": "ssh",
            "action_type": "command",
            "action": "whoami",
            "response_type": "deterministic",
            "latency_ms": 10,
            "session_depth": 1,
            "actor_label": "HUMAN",
        },
    )
    assert r.status_code == 200
    sessions = await client.get("/sessions")
    assert sessions.status_code == 200
    assert any(s["id"] == sid for s in sessions.json())


@pytest.mark.asyncio
async def test_deception_respond(client):
    r = await client.post(
        "/deception/respond",
        json={"service": "ssh", "command": "hostname", "hostname": "web-01"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["response"] == "web-01"


@pytest.mark.asyncio
async def test_recompute_empty(client):
    r = await client.post("/analysis/recompute")
    assert r.status_code == 200
    assert r.json()["sessions_processed"] == 0


@pytest.mark.asyncio
async def test_rate_limit_headers_size(client):
    r = await client.post(
        "/ingest/events",
        content=b"x" * 70000,
        headers={"content-type": "application/json", "content-length": "70000"},
    )
    assert r.status_code == 413
