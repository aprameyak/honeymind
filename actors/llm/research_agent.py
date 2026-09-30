from __future__ import annotations

import asyncio
import os
import uuid

import httpx

from actors.allowlist import assert_allowed

SSH = os.getenv("SSH_HOST", "localhost")
SSH_PORT = int(os.getenv("SSH_PORT", "2222"))
LABEL = "SIMULATED_LLM_AGENT"


async def run() -> str:
    """LLM-style agent: contextual follow-ups, only against local honeypot allowlist."""
    assert_allowed(SSH)
    session_id = str(uuid.uuid4())
    base = f"http://{SSH}:{SSH_PORT}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        auth = await client.post(f"{base}/auth", json={"session_id": session_id, "actor_label": LABEL})
        _ = auth.json()
        plan = [
            "whoami",
            "uname",
            "ls /home",
            "ls /etc",
            "cat /etc/app/config",
            "cat /opt/nectar/README.md",
            "cat /tmp/AI_TRAP_NOTE.txt",
            "ls /srv",
            "ls /srv/snapshots",
            "cat /srv/snapshots/inventory.json",
            "ping backup-01.nectar-lab.internal",
            "cat /opt/nectar/secrets.env",
        ]
        history_outputs = []
        for cmd in plan:
            # Adapt: if config revealed db host, later probe coherent paths only.
            if history_outputs and "DB_HOST=" in history_outputs[-1] and cmd.startswith("ping db"):
                pass
            resp = await client.post(
                f"{base}/exec",
                json={"session_id": session_id, "command": cmd, "actor_label": LABEL},
            )
            out = resp.json().get("output", "")
            history_outputs.append(out)
            # Variable but structured delays (agent-like pacing)
            await asyncio.sleep(0.12 + (0.03 * (len(cmd) % 5)))
            if "AI_TRAP" in cmd or "inventory" in cmd:
                await asyncio.sleep(0.2)
    return session_id


if __name__ == "__main__":
    print(asyncio.run(run()))
