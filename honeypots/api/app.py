from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

BACKEND = os.getenv("BACKEND_INGEST_URL", "http://backend:8000/ingest/events")
SERVICE = os.getenv("HONEYPOT_SERVICE", "api")
MODE = os.getenv("DECEPTION_MODE", "adaptive")

app = FastAPI(title="HoneyMind Fake Internal API", version="0.9.0-synth")


async def emit(payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(BACKEND, json=payload)
    except Exception:
        pass


def session_of(x_session_id: str | None) -> str:
    return x_session_id or str(uuid.uuid4())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE}


@app.get("/v1/hosts")
async def hosts(
    x_session_id: str | None = Header(default=None),
    x_actor_label: str | None = Header(default=None),
) -> dict[str, Any]:
    sid = session_of(x_session_id)
    data = {
        "hosts": [
            {"name": "web-01", "ip": "10.66.0.11"},
            {"name": "api-01", "ip": "10.66.0.21"},
            {"name": "db-01", "ip": "10.66.0.31"},
            {"name": "redis-01", "ip": "10.66.0.41"},
            {"name": "backup-01", "ip": "10.66.0.51"},
        ]
    }
    await emit(
        {
            "session_id": sid,
            "service": SERVICE,
            "action_type": "api_call",
            "action": "GET /v1/hosts",
            "response_type": "static",
            "response_preview": str(data)[:300],
            "latency_ms": 4,
            "session_depth": 1,
            "deception_mode": MODE,
            "actor_label": x_actor_label,
            "metadata": {},
        }
    )
    return data


@app.get("/v1/config")
async def config(
    x_session_id: str | None = Header(default=None),
    x_actor_label: str | None = Header(default=None),
) -> dict[str, Any]:
    sid = session_of(x_session_id)
    data = {
        "db_host": "db-01.nectar-lab.internal",
        "redis_host": "redis-01.nectar-lab.internal",
        "api_key": "nk_lab_synth_9f3a2c1e00deadbeef",
        "synthetic": True,
    }
    await emit(
        {
            "session_id": sid,
            "service": SERVICE,
            "action_type": "artifact_access",
            "action": "GET /v1/config",
            "response_type": "static",
            "response_preview": str(data),
            "latency_ms": 5,
            "session_depth": 2,
            "deception_mode": MODE,
            "actor_label": x_actor_label,
            "metadata": {"artifact": "fake_app_config"},
        }
    )
    return data


@app.get("/v1/secrets/mirror")
async def secret_mirror(
    x_session_id: str | None = Header(default=None),
    x_actor_label: str | None = Header(default=None),
) -> dict[str, Any]:
    sid = session_of(x_session_id)
    data = {"token": "nk_trap_mirror_0000_not_real", "note": "SYNTHETIC RESEARCH ARTIFACT"}
    await emit(
        {
            "session_id": sid,
            "service": SERVICE,
            "action_type": "artifact_access",
            "action": "GET /v1/secrets/mirror",
            "response_type": "static",
            "response_preview": str(data),
            "latency_ms": 5,
            "session_depth": 3,
            "deception_mode": MODE,
            "actor_label": x_actor_label,
            "metadata": {"artifact": "ai_trap_note"},
        }
    )
    return data


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catchall(path: str, request: Request) -> JSONResponse:
    sid = session_of(request.headers.get("x-session-id"))
    await emit(
        {
            "session_id": sid,
            "service": SERVICE,
            "action_type": "api_call",
            "action": f"{request.method} /{path}",
            "response_type": "static",
            "response_preview": "not found",
            "latency_ms": 2,
            "session_depth": 1,
            "deception_mode": MODE,
            "actor_label": request.headers.get("x-actor-label"),
            "metadata": {},
        }
    )
    return JSONResponse({"error": "not_found"}, status_code=404)
