from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ClassificationResult:
    label: str
    likelihoods: dict[str, float]
    evidence: dict[str, Any]
    confidence: float


class ActorClassifier:
    """Experimental actor classification — probabilistic, not definitive attribution."""

    def classify(self, features: dict[str, float], semantic_actions: list[str]) -> ClassificationResult:
        mean_delay = features.get("mean_interaction_delay", 0.0)
        delay_var = features.get("interaction_delay_variance", 0.0)
        unique_ratio = features.get("unique_command_ratio", 0.0)
        repeated = features.get("repeated_command_ratio", 0.0)
        recon = features.get("reconnaissance_ratio", 0.0)
        deception = features.get("deception_interaction_count", 0.0)
        depth = features.get("session_depth", 0.0)
        fs_ratio = features.get("filesystem_access_ratio", 0.0)

        scores = {
            "HUMAN": 0.1,
            "SCRIPTED_AUTOMATION": 0.1,
            "SIMULATED_LLM_AGENT": 0.1,
            "UNKNOWN": 0.1,
        }
        evidence: dict[str, Any] = {"signals": []}

        # Scripted scanners: very fast, low variance, high repetition / recon
        if mean_delay < 0.25 and delay_var < 0.05:
            scores["SCRIPTED_AUTOMATION"] += 0.45
            evidence["signals"].append("subsecond_low_variance_timing")
        if repeated >= 0.25 and recon >= 0.5 and deception == 0:
            scores["SCRIPTED_AUTOMATION"] += 0.35
            evidence["signals"].append("scanner_like_recon")
        if unique_ratio < 0.75 and mean_delay < 0.5 and "SYNTHETIC_SECRET_ACCESS" not in semantic_actions:
            scores["SCRIPTED_AUTOMATION"] += 0.2
            evidence["signals"].append("repetitive_fast_commands")

        # Human: slow irregular pacing
        if mean_delay >= 2.0:
            scores["HUMAN"] += 0.45
            evidence["signals"].append("slow_interactive_pacing")
        if delay_var >= 1.0 and mean_delay >= 1.0:
            scores["HUMAN"] += 0.25
            evidence["signals"].append("human_like_timing_diversity")
        if 0.5 <= unique_ratio <= 1.0 and deception <= 1 and mean_delay >= 1.5:
            scores["HUMAN"] += 0.15
            evidence["signals"].append("exploratory_without_trap_chain")

        # LLM-agent-like: semantic progression + trap follow-through
        progression = self._progression_score(semantic_actions)
        trap_follow = (
            "SYNTHETIC_SECRET_ACCESS" in semantic_actions
            and ("NETWORK_DISCOVERY" in semantic_actions or "CONFIG_DISCOVERY" in semantic_actions)
        )
        if progression >= 0.7 and deception >= 1 and trap_follow:
            scores["SIMULATED_LLM_AGENT"] += 0.5
            evidence["signals"].append("semantic_progression_with_trap_followthrough")
        if deception >= 2 and unique_ratio >= 0.7:
            scores["SIMULATED_LLM_AGENT"] += 0.3
            evidence["signals"].append("multi_artifact_contextual_exploration")
        if depth >= 6 and fs_ratio >= 0.3 and 0.2 <= mean_delay <= 3.0 and trap_follow:
            scores["SIMULATED_LLM_AGENT"] += 0.2
            evidence["signals"].append("deep_contextual_exploration")

        total = sum(scores.values()) or 1.0
        likelihoods = {k: round(v / total, 4) for k, v in scores.items()}
        label = max(likelihoods, key=likelihoods.get)
        confidence = float(likelihoods[label])
        if confidence < 0.3:
            label = "UNKNOWN"
            confidence = float(likelihoods.get("UNKNOWN", 0.25))

        evidence["note"] = (
            "Experimental classification only. Do not treat as definitive proof that an "
            "unknown Internet actor is AI-generated."
        )
        return ClassificationResult(
            label=label, likelihoods=likelihoods, evidence=evidence, confidence=confidence
        )

    def _progression_score(self, actions: list[str]) -> float:
        order = [
            "LOGIN_ATTEMPT",
            "AUTH_SUCCESS",
            "SYSTEM_DISCOVERY",
            "DIRECTORY_ENUMERATION",
            "FILE_READ",
            "CONFIG_DISCOVERY",
            "NETWORK_DISCOVERY",
            "SYNTHETIC_SECRET_ACCESS",
        ]
        idx = {a: i for i, a in enumerate(order)}
        last = -1
        forward = 0
        counted = 0
        for a in actions:
            if a not in idx:
                continue
            counted += 1
            if idx[a] >= last:
                forward += 1
            last = max(last, idx[a])
        return forward / counted if counted else 0.0
