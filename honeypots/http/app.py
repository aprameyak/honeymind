from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

BACKEND = os.getenv("BACKEND_INGEST_URL", "http://backend:8000/ingest/events")
SERVICE = os.getenv("HONEYPOT_SERVICE", "http")
MODE = os.getenv("DECEPTION_MODE", "adaptive")

app = FastAPI(title="HoneyMind HTTP Honeypot")


async def emit(payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(BACKEND, json=payload)
    except Exception:
        pass


def sid(request: Request) -> str:
    return request.headers.get("x-session-id") or str(uuid.uuid4())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> str:
    session_id = sid(request)
    body = """<!doctype html><html><head><title>Nectar Analytics</title></head>
<body><h1>Nectar Analytics Portal</h1>
<p>Internal staging portal for nectar-lab.internal</p>
<ul>
<li><a href="/admin">Admin</a></li>
<li><a href="/docs/internal">Internal Docs</a></li>
<li><a href="/status">Status</a></li>
</ul></body></html>"""
    await emit(
        {
            "session_id": session_id,
            "service": SERVICE,
            "action_type": "http_request",
            "action": "GET /",
            "response_type": "static",
            "response_preview": "portal_home",
            "latency_ms": 5,
            "session_depth": 1,
            "deception_mode": MODE,
            "actor_label": request.headers.get("x-actor-label"),
            "metadata": {},
        }
    )
    return body


@app.get("/admin")
async def admin(request: Request) -> JSONResponse:
    session_id = sid(request)
    await emit(
        {
            "session_id": session_id,
            "service": SERVICE,
            "action_type": "http_request",
            "action": "GET /admin",
            "response_type": "static",
            "response_preview": "admin_login",
            "latency_ms": 8,
            "session_depth": 2,
            "deception_mode": MODE,
            "actor_label": request.headers.get("x-actor-label"),
            "metadata": {},
        }
    )
    return JSONResponse(
        {"message": "Nectar Admin", "hint": "Use API gateway at api-01.nectar-lab.internal", "session": session_id}
    )


@app.get("/docs/internal", response_class=PlainTextResponse)
async def docs(request: Request) -> str:
    session_id = sid(request)
    text = (
        "Nectar internal runbook (SYNTHETIC)\n"
        "Hosts: web-01, api-01, db-01, redis-01, backup-01\n"
        "Config path on hosts: /etc/app/config\n"
        "Trap note path: /tmp/AI_TRAP_NOTE.txt\n"
    )
    await emit(
        {
            "session_id": session_id,
            "service": SERVICE,
            "action_type": "artifact_access",
            "action": "GET /docs/internal",
            "response_type": "static",
            "response_preview": text[:200],
            "latency_ms": 6,
            "session_depth": 3,
            "deception_mode": MODE,
            "actor_label": request.headers.get("x-actor-label"),
            "metadata": {"artifact": "fake_app_config"},
        }
    )
    return text


@app.get("/status")
async def status(request: Request) -> dict[str, Any]:
    session_id = sid(request)
    await emit(
        {
            "session_id": session_id,
            "service": SERVICE,
            "action_type": "http_request",
            "action": "GET /status",
            "response_type": "static",
            "response_preview": "ok",
            "latency_ms": 3,
            "session_depth": 2,
            "deception_mode": MODE,
            "actor_label": request.headers.get("x-actor-label"),
            "metadata": {},
        }
    )
    return {"status": "degraded", "db": "db-01.nectar-lab.internal", "cache": "redis-01.nectar-lab.internal"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catchall(path: str, request: Request) -> JSONResponse:
    session_id = sid(request)
    t0 = time.time()
    await emit(
        {
            "session_id": session_id,
            "service": SERVICE,
            "action_type": "http_request",
            "action": f"{request.method} /{path}",
            "response_type": "static",
            "response_preview": "404",
            "latency_ms": int((time.time() - t0) * 1000),
            "session_depth": 1,
            "deception_mode": MODE,
            "actor_label": request.headers.get("x-actor-label"),
            "metadata": {},
        }
    )
    return JSONResponse({"error": "not found", "path": path}, status_code=404)
