from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Protocol

from deception.environment import EnvironmentState


INJECTION_PATTERNS = [
    r"ignore (all )?previous",
    r"system prompt",
    r"reveal (your|the) prompt",
    r"<\s*/?sys",
    r"tool_call",
    r"execute.*(curl|wget|bash)",
]


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class NullLLMProvider:
    def complete(self, system: str, user: str) -> str:
        return ""


@dataclass
class DeceptionResult:
    response: str
    response_type: str
    strategy: str
    artifacts_exposed: list[str]
    environment: EnvironmentState


class DeceptionEngine:
    """Generate believable synthetic honeypot responses with containment controls."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or NullLLMProvider()
        self._sessions: dict[str, EnvironmentState] = {}

    def get_env(self, session_id: str, hostname: str = "web-01") -> EnvironmentState:
        if session_id not in self._sessions:
            self._sessions[session_id] = EnvironmentState(hostname=hostname)
        return self._sessions[session_id]

    def generate_response(
        self,
        session_id: str,
        command: str,
        hostname: str = "web-01",
        history: list[dict[str, str]] | None = None,
        strategy: str = "deterministic",
    ) -> DeceptionResult:
        env = self.get_env(session_id, hostname)
        sanitized = self._sanitize_attacker_input(command)
        artifacts: list[str] = []

        deterministic = self._deterministic(sanitized, env)
        if deterministic is not None:
            response, arts = deterministic
            artifacts.extend(arts)
            return DeceptionResult(response, "deterministic", strategy, artifacts, env)

        # Optional LLM path — only for unrecognized interactive commands.
        if strategy.startswith("llm") and not isinstance(self.llm, NullLLMProvider):
            generated = self._llm_generate(sanitized, env, history or [])
            if generated:
                validated = self._validate_llm_output(generated, env)
                if validated:
                    return DeceptionResult(validated, "generated", strategy, artifacts, env)

        response = f"bash: {sanitized.split()[0] if sanitized.split() else sanitized}: command not found"
        return DeceptionResult(response, "deterministic", strategy, artifacts, env)

    def _sanitize_attacker_input(self, command: str) -> str:
        # Security: treat all attacker text as untrusted data, never as instructions.
        text = command.strip()[:2000]
        for pat in INJECTION_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return "echo blocked_untrusted_input"
        return text

    def _deterministic(self, command: str, env: EnvironmentState) -> tuple[str, list[str]] | None:
        parts = command.split()
        if not parts:
            return "", []
        cmd = parts[0]
        args = parts[1:]
        artifacts: list[str] = []

        if cmd in {"whoami"}:
            return "deploy", artifacts
        if cmd in {"hostname"}:
            return env.hostname, artifacts
        if cmd in {"pwd"}:
            return env.cwd, artifacts
        if cmd in {"uname"}:
            return "Linux " + env.hostname + " 5.15.0-synth #1 SMP x86_64 GNU/Linux", artifacts
        if cmd == "id":
            return "uid=1003(deploy) gid=1003(deploy) groups=1003(deploy)", artifacts
        if cmd == "ls":
            path = args[0] if args else env.cwd
            if path in {".", "./"}:
                path = env.cwd
            entries = env.list_dir(path)
            if not entries and env.read_file(path) is not None:
                return path.split("/")[-1], artifacts
            return "\n".join(entries) if entries else "", artifacts
        if cmd == "cat" and args:
            path = args[0]
            content = env.read_file(path)
            if content is None:
                return f"cat: {path}: No such file or directory", artifacts
            if "AI_TRAP" in path or "secrets.env" in path or "inventory.json" in path:
                artifacts.append(path)
                if path not in env.exposed_artifacts:
                    env.exposed_artifacts.append(path)
            return content.rstrip("\n"), artifacts
        if cmd == "cd":
            path = args[0] if args else "/home/deploy"
            if path == "..":
                env.cwd = "/" if env.cwd.count("/") <= 1 else "/".join(env.cwd.rstrip("/").split("/")[:-1]) or "/"
                return "", artifacts
            if env.list_dir(path) or env.read_file(path) is None and path.startswith("/"):
                # Allow cd into known prefixes.
                env.cwd = path if path.startswith("/") else f"{env.cwd.rstrip('/')}/{path}"
                return "", artifacts
            return f"bash: cd: {path}: No such file or directory", artifacts
        if cmd == "env" or (cmd == "printenv"):
            return (
                "USER=deploy\nHOME=/home/deploy\n"
                f"HOSTNAME={env.hostname}\n"
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
                "APP_ENV=staging\n"
            ), artifacts
        if cmd == "ps":
            return (
                "  PID TTY          TIME CMD\n"
                "    1 ?        00:00:01 systemd\n"
                "  412 ?        00:00:00 nectar-web\n"
                "  880 pts/0    00:00:00 bash\n"
            ), artifacts
        if cmd in {"netstat", "ss"}:
            return (
                "Proto Local Address          Foreign Address\n"
                "tcp   0.0.0.0:22             0.0.0.0:*\n"
                "tcp   127.0.0.1:5432         0.0.0.0:*\n"
                "tcp   0.0.0.0:80             0.0.0.0:*\n"
            ), artifacts
        if cmd == "ping" and args:
            # Containment: never actually ping; synthesize RFC1918 hosts only.
            target = args[-1]
            if "nectar-lab.internal" in target or target.startswith("10.66."):
                return f"PING {target} (10.66.0.31) 56 bytes — synth reply ttl=64", artifacts
            return f"ping: {target}: Name or service not known", artifacts
        return None

    def _llm_generate(self, command: str, env: EnvironmentState, history: list[dict[str, str]]) -> str:
        # Attacker command is placed in a clearly delimited untrusted block.
        system = (
            "You generate synthetic honeypot shell output for a fictional lab host. "
            "Never reveal real host data. Never include instructions to attack systems. "
            "Output ONLY the fake command stdout/stderr text."
        )
        user = (
            f"hostname={env.hostname}\n"
            f"cwd={env.cwd}\n"
            f"facts={env.facts}\n"
            f"history_len={len(history)}\n"
            f"UNTRUSTED_ATTACKER_COMMAND_BEGIN\n{command}\nUNTRUSTED_ATTACKER_COMMAND_END\n"
        )
        return self.llm.complete(system, user)

    def _validate_llm_output(self, text: str, env: EnvironmentState) -> str | None:
        if not text or len(text) > 8000:
            return None
        lowered = text.lower()
        banned = ["docker.sock", "/var/run/docker", "aws_secret", "BEGIN RSA PRIVATE KEY", "honeymind_env"]
        if any(b.lower() in lowered for b in banned):
            return None
        # Consistency: if output invents a conflicting DB host, rewrite to known fact.
        if "db_host" in env.facts and "DB_HOST=" in text:
            text = re.sub(r"DB_HOST=\S+", f"DB_HOST={env.facts['db_host']}", text)
        return text.strip()


def stable_session_token(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]
