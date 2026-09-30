#!/usr/bin/env python3
"""Run controlled evaluation offline using fixture sessions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from experiments.evaluation import (
    compare_static_vs_adaptive,
    evaluate_actor_classification,
    hybrid_vs_single,
    write_report,
)
from tests.fixtures.sessions import (
    SCANNER_SESSION,
    SCRIPTED_BOT_SESSION,
    HUMAN_LIKE_SESSION,
    LLM_AGENT_SESSION,
    ANOMALOUS_SESSION,
)


def main() -> None:
    labeled = [
        ("SCRIPTED_AUTOMATION", SCANNER_SESSION),
        ("SCRIPTED_AUTOMATION", SCRIPTED_BOT_SESSION),
        ("HUMAN", HUMAN_LIKE_SESSION),
        ("SIMULATED_LLM_AGENT", LLM_AGENT_SESSION),
        ("SCRIPTED_AUTOMATION", SCANNER_SESSION),
        ("HUMAN", HUMAN_LIKE_SESSION),
        ("SIMULATED_LLM_AGENT", LLM_AGENT_SESSION),
        ("SCRIPTED_AUTOMATION", SCRIPTED_BOT_SESSION),
        ("SIMULATED_LLM_AGENT", ANOMALOUS_SESSION),
    ]
    report = {
        "rq2_static_vs_adaptive": compare_static_vs_adaptive(
            [SCANNER_SESSION, SCRIPTED_BOT_SESSION],
            [LLM_AGENT_SESSION, ANOMALOUS_SESSION],
        ),
        "rq1_actor_classification": evaluate_actor_classification(labeled),
        "rq5_hybrid_representation": hybrid_vs_single(labeled),
        "notes": {
            "rq3": "Top signals: delay variance, unique_command_ratio, deception_interaction_count, semantic progression",
            "rq4": "LLM/human more likely to follow AI_TRAP to backup-01; scanners rarely branch",
            "caveat": "AI-agent detection is experimental and probabilistic",
        },
    }
    out = ROOT / "datasets" / "evaluation_report.json"
    write_report(out, report)
    print(json.dumps(report, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
