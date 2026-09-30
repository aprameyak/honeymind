from __future__ import annotations

import asyncio
import os
import uuid

import httpx

from actors.allowlist import assert_allowed

SSH = os.getenv("SSH_HOST", "localhost")
SSH_PORT = int(os.getenv("SSH_PORT", "2222"))
HTTP = os.getenv("HTTP_URL", "http://localhost:8080")
API = os.getenv("API_URL", "http://localhost:8081")
LABEL = "SCRIPTED_AUTOMATION"


async def run() -> str:
    assert_allowed(SSH)
    assert_allowed(HTTP)
    assert_allowed(API)
    session_id = str(uuid.uuid4())
    ssh = f"http://{SSH}:{SSH_PORT}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(f"{ssh}/auth", json={"session_id": session_id, "actor_label": LABEL})
        for cmd in [
            "whoami",
            "hostname",
            "ls /",
            "ls /etc",
            "cat /etc/app/config",
            "ls /opt/nectar",
            "cat /opt/nectar/deploy.yml",
            "ping db-01.nectar-lab.internal",
        ]:
            await client.post(f"{ssh}/exec", json={"session_id": session_id, "command": cmd, "actor_label": LABEL})
            await asyncio.sleep(0.08)
        headers = {"x-session-id": session_id, "x-actor-label": LABEL}
        await client.get(f"{HTTP}/", headers=headers)
        await client.get(f"{HTTP}/admin", headers=headers)
        await client.get(f"{API}/v1/hosts", headers=headers)
        await client.get(f"{API}/v1/config", headers=headers)
    return session_id


if __name__ == "__main__":
    print(asyncio.run(run()))
