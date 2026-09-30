"""Containment / compose safety checks (static analysis of docker-compose)."""

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_compose_no_privileged_or_docker_socket():
    raw = (ROOT / "docker-compose.yml").read_text()
    data = yaml.safe_load(raw)
    for name, svc in data["services"].items():
        assert not svc.get("privileged"), f"{name} must not be privileged"
        assert svc.get("network_mode") != "host", f"{name} must not use host network"
        volumes = svc.get("volumes") or []
        for v in volumes:
            s = str(v)
            assert "/var/run/docker.sock" not in s
            assert not s.startswith("/:/")
        if name.startswith("honeypot"):
            assert "cap_drop" in svc
            assert "ALL" in svc["cap_drop"]
            assert svc.get("security_opt")


def test_env_example_has_no_aws_keys():
    text = (ROOT / ".env.example").read_text()
    assert "AKIA" not in text
