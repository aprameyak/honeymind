from __future__ import annotations

import re
from typing import Any


RECON_CMDS = {"whoami", "uname", "id", "hostname", "ps", "env", "printenv", "netstat", "ss", "ping"}
FS_CMDS = {"ls", "cat", "cd", "find", "head", "tail", "less", "more"}
CONFIG_PATHS = ("/etc/app/config", "deploy.yml", "config")
SECRET_PATHS = ("secrets.env", "AI_TRAP", "inventory.json", "FAKE_API_KEY", "nk_")


def normalize_action(action: str, action_type: str = "command") -> str:
    a = action.strip().lower()
    if action_type == "auth" or a.startswith("login") or "password" in a and "auth" in action_type:
        if "success" in a or action_type == "auth_success":
            return "AUTH_SUCCESS"
        return "LOGIN_ATTEMPT"
    if action_type in {"http_request", "api_call"}:
        if "/admin" in a or "/internal" in a:
            return "NETWORK_DISCOVERY"
        if "config" in a or "secret" in a:
            return "CONFIG_DISCOVERY"
        return "NETWORK_DISCOVERY"
    cmd = a.split()[0] if a.split() else a
    if cmd in {"whoami", "uname", "id", "hostname"}:
        return "SYSTEM_DISCOVERY"
    if cmd in {"ls", "find", "tree"}:
        return "DIRECTORY_ENUMERATION"
    if cmd == "cat" or cmd in {"head", "tail"}:
        path = " ".join(a.split()[1:])
        if any(s.lower() in path for s in SECRET_PATHS):
            return "SYNTHETIC_SECRET_ACCESS"
        if any(c in path for c in CONFIG_PATHS):
            return "CONFIG_DISCOVERY"
        return "FILE_READ"
    if cmd in {"ping", "netstat", "ss", "curl", "wget"}:
        return "NETWORK_DISCOVERY"
    if cmd == "cd":
        return "DIRECTORY_ENUMERATION"
    if cmd in {"env", "printenv", "ps"}:
        return "SYSTEM_DISCOVERY"
    return "GENERIC_ACTION"


def build_session_summary(semantic_actions: list[str], service: str) -> str:
    parts = [f"Actor interacted with the {service} honeypot."]
    mapping = {
        "LOGIN_ATTEMPT": "Attempted authentication.",
        "AUTH_SUCCESS": "Actor authenticated through the decoy service.",
        "SYSTEM_DISCOVERY": "Performed operating-system discovery.",
        "DIRECTORY_ENUMERATION": "Enumerated directories.",
        "FILE_READ": "Inspected files.",
        "CONFIG_DISCOVERY": "Inspected application configuration.",
        "NETWORK_DISCOVERY": "Attempted additional internal discovery.",
        "SYNTHETIC_SECRET_ACCESS": "Accessed a synthetic credential artifact.",
        "GENERIC_ACTION": "Issued additional commands.",
    }
    seen = set()
    for action in semantic_actions:
        if action in seen:
            continue
        seen.add(action)
        parts.append(mapping.get(action, "Continued interaction."))
    return " ".join(parts)


def extract_features(events: list[dict[str, Any]]) -> dict[str, float]:
    if not events:
        return {
            "session_duration": 0.0,
            "command_count": 0.0,
            "mean_interaction_delay": 0.0,
            "interaction_delay_variance": 0.0,
            "unique_command_ratio": 0.0,
            "repeated_command_ratio": 0.0,
            "reconnaissance_ratio": 0.0,
            "filesystem_access_ratio": 0.0,
            "deception_interaction_count": 0.0,
            "session_depth": 0.0,
            "auth_attempt_count": 0.0,
            "unique_resources": 0.0,
        }

    timestamps = [e["timestamp"] for e in events]
    duration = max((timestamps[-1] - timestamps[0]).total_seconds(), 0.0)
    actions = [e.get("action", "") for e in events]
    command_count = float(len(actions))
    unique = len(set(actions))
    unique_ratio = unique / command_count if command_count else 0.0
    repeated_ratio = 1.0 - unique_ratio

    delays = []
    for i in range(1, len(timestamps)):
        delays.append(max((timestamps[i] - timestamps[i - 1]).total_seconds(), 0.0))
    mean_delay = sum(delays) / len(delays) if delays else 0.0
    var_delay = (
        sum((d - mean_delay) ** 2 for d in delays) / len(delays) if delays else 0.0
    )

    recon = 0
    fs = 0
    auth = 0
    deception = 0
    resources: set[str] = set()
    for e in events:
        a = e.get("action", "")
        cmd = a.split()[0] if a.split() else ""
        if cmd in RECON_CMDS:
            recon += 1
        if cmd in FS_CMDS:
            fs += 1
        if e.get("action_type", "").startswith("auth") or "login" in a.lower():
            auth += 1
        if any(s.lower() in a.lower() for s in SECRET_PATHS) or e.get("action_type") == "artifact_access":
            deception += 1
        for token in re.findall(r"(/[\w./-]+)", a):
            resources.add(token)

    depth = max((e.get("session_depth", 0) for e in events), default=0)
    return {
        "session_duration": float(duration),
        "command_count": command_count,
        "mean_interaction_delay": float(mean_delay),
        "interaction_delay_variance": float(var_delay),
        "unique_command_ratio": float(unique_ratio),
        "repeated_command_ratio": float(repeated_ratio),
        "reconnaissance_ratio": recon / command_count if command_count else 0.0,
        "filesystem_access_ratio": fs / command_count if command_count else 0.0,
        "deception_interaction_count": float(deception),
        "session_depth": float(depth),
        "auth_attempt_count": float(auth),
        "unique_resources": float(len(resources)),
    }


FEATURE_KEYS = [
    "session_duration",
    "command_count",
    "mean_interaction_delay",
    "interaction_delay_variance",
    "unique_command_ratio",
    "repeated_command_ratio",
    "reconnaissance_ratio",
    "filesystem_access_ratio",
    "deception_interaction_count",
    "session_depth",
    "auth_attempt_count",
    "unique_resources",
]


def normalize_features(vectors: list[dict[str, float]]) -> list[dict[str, float]]:
    if not vectors:
        return []
    mins = {k: min(v[k] for v in vectors) for k in FEATURE_KEYS}
    maxs = {k: max(v[k] for v in vectors) for k in FEATURE_KEYS}
    out = []
    for vec in vectors:
        norm = {}
        for k in FEATURE_KEYS:
            span = maxs[k] - mins[k]
            norm[k] = 0.0 if span == 0 else (vec[k] - mins[k]) / span
        out.append(norm)
    return out


def vector_as_list(features: dict[str, float]) -> list[float]:
    return [float(features.get(k, 0.0)) for k in FEATURE_KEYS]
