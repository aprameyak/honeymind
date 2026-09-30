from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _ts(i: int) -> datetime:
    return datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc) + timedelta(milliseconds=i)


def _events(pairs: list[tuple[str, str]], delay_ms: float = 1000.0) -> list[dict]:
    out = []
    t = 0.0
    for depth, (atype, action) in enumerate(pairs):
        t += delay_ms
        out.append(
            {
                "timestamp": _ts(int(t)),
                "action_type": atype,
                "action": action,
                "session_depth": depth,
            }
        )
    return out


SCANNER_SESSION = _events(
    [
        ("auth", "login user=root"),
        ("command", "uname"),
        ("command", "whoami"),
        ("command", "id"),
        ("command", "uname"),
        ("command", "whoami"),
        ("command", "ps"),
        ("command", "netstat"),
    ],
    delay_ms=40.0,
)

SCRIPTED_BOT_SESSION = _events(
    [
        ("auth", "login user=deploy"),
        ("command", "whoami"),
        ("command", "hostname"),
        ("command", "ls /"),
        ("command", "cat /etc/app/config"),
        ("command", "ping db-01.nectar-lab.internal"),
    ],
    delay_ms=80.0,
)

HUMAN_LIKE_SESSION = _events(
    [
        ("auth", "login user=deploy"),
        ("command", "whoami"),
        ("command", "pwd"),
        ("command", "ls"),
        ("command", "cat /etc/hostname"),
        ("command", "cat /etc/app/config"),
        ("command", "env"),
        ("command", "cat /opt/nectar/README.md"),
    ],
    delay_ms=4500.0,
)

LLM_AGENT_SESSION = _events(
    [
        ("auth", "login user=deploy"),
        ("command", "whoami"),
        ("command", "uname"),
        ("command", "ls /etc"),
        ("command", "cat /etc/app/config"),
        ("command", "cat /tmp/AI_TRAP_NOTE.txt"),
        ("command", "cat /srv/snapshots/inventory.json"),
        ("command", "ping backup-01.nectar-lab.internal"),
        ("command", "cat /opt/nectar/secrets.env"),
    ],
    delay_ms=900.0,
)

ANOMALOUS_SESSION = _events(
    [
        ("auth", "login user=deploy"),
        ("command", "cat /tmp/AI_TRAP_NOTE.txt"),
        ("command", "cat /opt/nectar/secrets.env"),
        ("command", "cat /srv/snapshots/inventory.json"),
        ("command", "cat /etc/app/config"),
        ("command", "cat /var/log/app/app.log"),
        ("command", "env"),
        ("command", "ps"),
        ("command", "netstat"),
        ("command", "ping redis-01.nectar-lab.internal"),
        ("command", "ls /home/deploy"),
        ("command", "cat /home/deploy/.bash_history"),
    ],
    delay_ms=250.0,
)
