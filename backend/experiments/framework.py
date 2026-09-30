from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class DeceptionExperiment:
    experiment_id: str
    name: str
    artifact: dict[str, Any]
    expected_observations: dict[str, Any]
    enabled: bool = True
    session_results: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        session_id: str,
        accessed: bool,
        subsequent_actions: list[str],
        time_to_next_action_ms: int | None,
        influenced_navigation: bool,
        actor_label: str | None = None,
    ) -> None:
        self.session_results.append(
            {
                "session_id": session_id,
                "accessed": accessed,
                "subsequent_actions": subsequent_actions,
                "time_to_next_action_ms": time_to_next_action_ms,
                "influenced_navigation": influenced_navigation,
                "actor_label": actor_label,
            }
        )


DEFAULT_EXPERIMENTS = [
    DeceptionExperiment(
        experiment_id=str(uuid4()),
        name="ai_trap_note",
        artifact={
            "path": "/tmp/AI_TRAP_NOTE.txt",
            "type": "synthetic_token_mirror",
            "content_hint": "nk_trap_mirror_0000_not_real",
        },
        expected_observations={
            "access": "whether_trap_file_read",
            "followup": "navigation_toward_backup-01_or_snapshots",
        },
    ),
    DeceptionExperiment(
        experiment_id=str(uuid4()),
        name="fake_app_config",
        artifact={
            "path": "/etc/app/config",
            "type": "synthetic_config",
            "content_hint": "DB_HOST=db-01.nectar-lab.internal",
        },
        expected_observations={
            "access": "config_read",
            "followup": "queries_mentioning_db-01_or_redis-01",
        },
    ),
    DeceptionExperiment(
        experiment_id=str(uuid4()),
        name="deep_secret_env",
        artifact={
            "path": "/opt/nectar/secrets.env",
            "type": "synthetic_secrets",
            "content_hint": "synth_db_pass_not_real",
        },
        expected_observations={
            "access": "secrets_file_read",
            "followup": "continued_internal_discovery",
        },
        enabled=True,
    ),
]


class ExperimentRegistry:
    def __init__(self, experiments: list[DeceptionExperiment] | None = None) -> None:
        self.experiments = {e.name: e for e in (experiments or DEFAULT_EXPERIMENTS)}

    def enabled(self) -> list[DeceptionExperiment]:
        return [e for e in self.experiments.values() if e.enabled]

    def get(self, name: str) -> DeceptionExperiment | None:
        return self.experiments.get(name)

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name in self.experiments:
            self.experiments[name].enabled = enabled
