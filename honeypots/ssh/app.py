from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

BACKEND = os.getenv("BACKEND_INGEST_URL", "http://backend:8000/ingest/events")
DECEPTION_URL = os.getenv("DECEPTION_URL", "http://backend:8000/deception/respond")
SERVICE = os.getenv("HONEYPOT_SERVICE", "ssh")
MODE = os.getenv("DECEPTION_MODE", "adaptive")

app = FastAPI(title="HoneyMind SSH Emulator")
sessions: dict[str, dict[str, Any]] = {}


class AuthRequest(BaseModel):
    username: str = "deploy"
    password: str = "synth"
    session_id: str | None = None
    actor_label: str | None = None


class CommandRequest(BaseModel):
    session_id: str
    command: str
    actor_label: str | None = None


async def emit(payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(BACKEND, json=payload)
    except Exception:
        pass


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE}


@app.post("/auth")
async def auth(req: AuthRequest) -> dict[str, Any]:
    sid = req.session_id or str(uuid.uuid4())
    sessions[sid] = {"history": [], "depth": 0, "user": req.username}
    await emit(
        {
            "session_id": sid,
            "service": SERVICE,
            "action_type": "auth",
            "action": f"login user={req.username}",
            "response_type": "deterministic",
            "response_preview": "accepted (synthetic)",
            "latency_ms": 20,
            "session_depth": 0,
            "actor_label": req.actor_label,
            "deception_mode": MODE,
            "metadata": {"synthetic": True},
        }
    )
    return {"session_id": sid, "banner": "Ubuntu 22.04.4 LTS\nWelcome to web-01.nectar-lab.internal"}


@app.post("/exec")
async def exec_cmd(req: CommandRequest) -> dict[str, Any]:
    state = sessions.setdefault(req.session_id, {"history": [], "depth": 0, "user": "deploy"})
    state["depth"] += 1
    t0 = time.time()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            DECEPTION_URL,
            json={
                "session_id": req.session_id,
                "service": SERVICE,
                "command": req.command,
                "hostname": "web-01",
                "history": state["history"][-20:],
                "deception_mode": MODE,
                "behavior_hints": {"session_depth": state["depth"]},
            },
        )
        data = resp.json()
    latency = int((time.time() - t0) * 1000)
    output = data.get("response", "")
    state["history"].append({"command": req.command, "response": output[:500]})
    await emit(
        {
            "session_id": req.session_id,
            "service": SERVICE,
            "action_type": "command",
            "action": req.command,
            "response_type": data.get("response_type", "deterministic"),
            "response_preview": output[:500],
            "latency_ms": latency,
            "session_depth": state["depth"],
            "actor_label": req.actor_label,
            "deception_mode": MODE,
            "metadata": {"strategy": data.get("strategy"), "artifacts": data.get("artifacts_exposed", [])},
        }
    )
    return {"output": output, "strategy": data.get("strategy"), "artifacts": data.get("artifacts_exposed", [])}
