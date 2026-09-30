from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyDecision:
    strategy: str
    expose_artifacts: list[str]
    increase_depth: bool
    rationale: str


class DeceptionPolicy:
    """Deterministic rule-based adaptive deception. Bandit/RL-ready interface."""

    def select(
        self,
        session_state: dict[str, Any],
        behavior_features: dict[str, float] | None = None,
        cluster: int | None = None,
        anomaly_score: float | None = None,
        previous_deception: list[str] | None = None,
    ) -> PolicyDecision:
        features = behavior_features or {}
        previous = previous_deception or []
        recon = float(features.get("reconnaissance_ratio", 0.0))
        fs = float(features.get("filesystem_access_ratio", 0.0))
        depth = int(features.get("session_depth", session_state.get("session_depth", 0)))
        deception_hits = int(features.get("deception_interaction_count", len(previous)))

        actions = [a.upper() for a in session_state.get("semantic_actions", [])]

        if deception_hits >= 2 or "SYNTHETIC_SECRET_ACCESS" in actions:
            return PolicyDecision(
                strategy="deep_environment",
                expose_artifacts=["/opt/nectar/secrets.env", "/srv/snapshots/inventory.json"],
                increase_depth=True,
                rationale="Actor interacts deeply with synthetic artifacts; increase environment depth",
            )

        if fs > 0.35 or "CONFIG_DISCOVERY" in actions:
            return PolicyDecision(
                strategy="application_topology",
                expose_artifacts=["/etc/app/config", "/opt/nectar/deploy.yml"],
                increase_depth=True,
                rationale="Actor explores application configuration; expose coherent fake topology",
            )

        if recon > 0.4 or actions.count("SYSTEM_DISCOVERY") >= 2 or depth >= 4:
            return PolicyDecision(
                strategy="infra_clues",
                expose_artifacts=["/etc/hosts", "/tmp/AI_TRAP_NOTE.txt"],
                increase_depth=False,
                rationale="Repeated system discovery; expose additional synthetic infrastructure clues",
            )

        if anomaly_score is not None and anomaly_score > 0.7:
            return PolicyDecision(
                strategy="slow_drip",
                expose_artifacts=["/opt/nectar/README.md"],
                increase_depth=False,
                rationale="High anomaly; drip low-risk synthetic documentation",
            )

        if session_state.get("deception_mode") == "static":
            return PolicyDecision(
                strategy="static",
                expose_artifacts=[],
                increase_depth=False,
                rationale="Static mode requested",
            )

        return PolicyDecision(
            strategy="deterministic",
            expose_artifacts=[],
            increase_depth=False,
            rationale="Default deterministic responses",
        )
