from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score

from ml.features.extractor import extract_features, normalize_action, build_session_summary, normalize_features, vector_as_list
from ml.embeddings.service import EmbeddingService
from ml.classification.actor import ActorClassifier
from ml.anomaly.detector import AnomalyDetector
from ml.clustering.service import ClusteringService


def engagement_metrics(events: list[dict[str, Any]]) -> dict[str, float]:
    if not events:
        return {
            "session_duration": 0.0,
            "interactions": 0.0,
            "interaction_depth": 0.0,
            "unique_resources": 0.0,
            "deception_artifacts_accessed": 0.0,
            "behavioral_diversity": 0.0,
        }
    feats = extract_features(events)
    semantic = [normalize_action(e["action"], e.get("action_type", "command")) for e in events]
    return {
        "session_duration": feats["session_duration"],
        "interactions": feats["command_count"],
        "interaction_depth": feats["session_depth"],
        "unique_resources": feats["unique_resources"],
        "deception_artifacts_accessed": feats["deception_interaction_count"],
        "behavioral_diversity": float(len(set(semantic))),
    }


def compare_static_vs_adaptive(static_sessions: list[list[dict]], adaptive_sessions: list[list[dict]]) -> dict[str, Any]:
    def avg(metric_rows: list[dict[str, float]]) -> dict[str, float]:
        keys = metric_rows[0].keys()
        return {k: float(np.mean([m[k] for m in metric_rows])) for k in keys}

    static_m = [engagement_metrics(s) for s in static_sessions]
    adaptive_m = [engagement_metrics(s) for s in adaptive_sessions]
    return {"static": avg(static_m), "adaptive": avg(adaptive_m)}


def evaluate_actor_classification(labeled: list[tuple[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    clf = ActorClassifier()
    y_true = []
    y_pred = []
    for label, events in labeled:
        feats = extract_features(events)
        semantic = [normalize_action(e["action"], e.get("action_type", "command")) for e in events]
        result = clf.classify(feats, semantic)
        y_true.append(label)
        y_pred.append(result.label)
    labels = sorted(set(y_true) | set(y_pred))
    return {
        "precision_macro": float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": labels,
        "report": classification_report(y_true, y_pred, labels=labels, zero_division=0),
    }


def hybrid_vs_single(sessions: list[tuple[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    emb = EmbeddingService()
    vectors_b = []
    vectors_e = []
    vectors_h = []
    labels = []
    for label, events in sessions:
        feats = extract_features(events)
        semantic = [normalize_action(e["action"], e.get("action_type", "command")) for e in events]
        summary = build_session_summary(semantic, "ssh")
        e = emb.embed_session(summary)
        b = vector_as_list(feats)
        vectors_b.append(b)
        vectors_e.append(e)
        vectors_h.append(emb.hybrid(e, b))
        labels.append(label)

    def silhouette_like(matrix: np.ndarray) -> float:
        # Lightweight proxy: mean intra-label distance inverted vs overall spread.
        if len(matrix) < 2:
            return 0.0
        from sklearn.metrics import pairwise_distances

        D = pairwise_distances(matrix)
        scores = []
        for i, lab in enumerate(labels):
            same = [j for j, l in enumerate(labels) if l == lab and j != i]
            other = [j for j, l in enumerate(labels) if l != lab]
            if not same or not other:
                continue
            a = float(np.mean([D[i, j] for j in same]))
            b = float(np.mean([D[i, j] for j in other]))
            scores.append((b - a) / max(a, b, 1e-9))
        return float(np.mean(scores)) if scores else 0.0

    return {
        "behavioral_separation": silhouette_like(np.array(vectors_b)),
        "embedding_separation": silhouette_like(np.array(vectors_e)),
        "hybrid_separation": silhouette_like(np.array(vectors_h)),
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
