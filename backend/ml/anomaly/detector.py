from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest

from ml.features.extractor import FEATURE_KEYS


@dataclass
class AnomalyResult:
    scores: list[float]
    is_anomaly: list[bool]
    contributions: list[dict[str, float]]
    params: dict[str, Any]


class AnomalyDetector:
    def __init__(self, contamination: float = 0.15, random_seed: int = 42) -> None:
        self.contamination = contamination
        self.random_seed = random_seed
        self.model: IsolationForest | None = None
        self._train_mean: np.ndarray | None = None

    def fit(self, sessions: np.ndarray) -> "AnomalyDetector":
        if sessions.size == 0:
            return self
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_seed,
            n_estimators=100,
        )
        self.model.fit(sessions)
        self._train_mean = sessions.mean(axis=0)
        return self

    def score(self, session: np.ndarray) -> tuple[float, bool, dict[str, float]]:
        if self.model is None:
            return 0.0, False, {}
        x = session.reshape(1, -1)
        # Higher score => more anomalous (invert sklearn decision_function)
        raw = float(self.model.decision_function(x)[0])
        anomaly_score = float(max(0.0, min(1.0, 0.5 - raw)))
        pred = int(self.model.predict(x)[0])
        is_anom = pred == -1
        contrib: dict[str, float] = {}
        if self._train_mean is not None:
            delta = np.abs(session - self._train_mean)
            for i, key in enumerate(FEATURE_KEYS[: len(delta)]):
                contrib[key] = float(delta[i])
            total = sum(contrib.values()) or 1.0
            contrib = {k: v / total for k, v in contrib.items()}
        return anomaly_score, is_anom, contrib

    def score_many(self, matrix: np.ndarray) -> AnomalyResult:
        scores: list[float] = []
        flags: list[bool] = []
        contribs: list[dict[str, float]] = []
        for row in matrix:
            s, f, c = self.score(row)
            scores.append(s)
            flags.append(f)
            contribs.append(c)
        return AnomalyResult(
            scores=scores,
            is_anomaly=flags,
            contributions=contribs,
            params={"contamination": self.contamination, "random_seed": self.random_seed},
        )
