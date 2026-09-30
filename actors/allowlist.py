from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

# Containment: simulated actors may only contact these lab hostnames.
DEFAULT_ALLOWLIST = {
    "honeypot-ssh",
    "honeypot-http",
    "honeypot-api",
    "backend",
    "localhost",
    "127.0.0.1",
}


def get_allowlist() -> set[str]:
    raw = os.getenv("ALLOWLIST", "")
    extra = {x.strip() for x in raw.split(",") if x.strip()}
    return DEFAULT_ALLOWLIST | extra


def assert_allowed(url_or_host: str) -> None:
    host = url_or_host
    if "://" in url_or_host:
        host = urlparse(url_or_host).hostname or ""
    allow = get_allowlist()
    if host not in allow:
        raise PermissionError(f"Actor blocked: host {host!r} not in lab allowlist {sorted(allow)}")


def resolve_ok(host: str) -> bool:
    assert_allowed(host)
    try:
        socket.getaddrinfo(host, None)
        return True
    except OSError:
        return False
