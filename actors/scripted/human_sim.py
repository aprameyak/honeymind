from __future__ import annotations

import asyncio
import os
import uuid

import httpx

from actors.allowlist import assert_allowed

SSH = os.getenv("SSH_HOST", "localhost")
SSH_PORT = int(os.getenv("SSH_PORT", "2222"))
LABEL = "HUMAN"


async def run() -> str:
    """Human-like pacing with exploratory but imperfect command sequences."""
    assert_allowed(SSH)
    session_id = str(uuid.uuid4())
    base = f"http://{SSH}:{SSH_PORT}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.post(f"{base}/auth", json={"session_id": session_id, "actor_label": LABEL})
        cmds = [
            "whoami",
            "pwd",
            "ls",
            "ls /tmp",
            "cat /etc/hostname",
            "ls /etc",
            "cat /etc/app/config",
            "env",
            "ls /opt/nectar",
            "cat /opt/nectar/README.md",
        ]
        for i, cmd in enumerate(cmds):
            await client.post(f"{base}/exec", json={"session_id": session_id, "command": cmd, "actor_label": LABEL})
            # Irregular human-like delays
            await asyncio.sleep(0.4 + (0.35 if i % 3 == 0 else 0.1) + (0.25 if i % 4 == 0 else 0))
    return session_id


if __name__ == "__main__":
    print(asyncio.run(run()))
