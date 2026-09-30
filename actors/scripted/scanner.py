from __future__ import annotations

import asyncio
import os
import uuid

import httpx

from actors.allowlist import assert_allowed

SSH = os.getenv("SSH_HOST", "localhost")
SSH_PORT = int(os.getenv("SSH_PORT", "2222"))
LABEL = "SCRIPTED_AUTOMATION"


async def run() -> str:
    base = f"http://{SSH}:{SSH_PORT}"
    assert_allowed(SSH)
    session_id = str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(f"{base}/auth", json={"session_id": session_id, "actor_label": LABEL, "username": "root"})
        for cmd in ["uname", "whoami", "id", "uname", "whoami", "ps", "netstat"]:
            await client.post(
                f"{base}/exec",
                json={"session_id": session_id, "command": cmd, "actor_label": LABEL},
            )
            await asyncio.sleep(0.05)
    return session_id


if __name__ == "__main__":
    print(asyncio.run(run()))
