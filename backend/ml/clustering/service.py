from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA


@dataclass
class ClusterResult:
    labels: list[int]
    clusters: list[dict[str, Any]]
    coords_2d: list[list[float]]
    params: dict[str, Any]


class ClusteringService:
    def __init__(self, eps: float = 0.8, min_samples: int = 2, algorithm: str = "dbscan") -> None:
        self.eps = eps
        self.min_samples = min_samples
        self.algorithm = algorithm

    def fit_predict(
        self,
        matrix: np.ndarray,
        session_ids: list[str],
        semantic_actions: list[list[str]] | None = None,
    ) -> ClusterResult:
        if matrix.size == 0 or len(session_ids) == 0:
            return ClusterResult([], [], [], {"eps": self.eps, "min_samples": self.min_samples})

        if self.algorithm == "hdbscan":
            try:
                import hdbscan  # type: ignore

                model = hdbscan.HDBSCAN(min_cluster_size=self.min_samples)
                labels = model.fit_predict(matrix)
            except Exception:
                model = DBSCAN(eps=self.eps, min_samples=self.min_samples)
                labels = model.fit_predict(matrix)
        else:
            model = DBSCAN(eps=self.eps, min_samples=self.min_samples)
            labels = model.fit_predict(matrix)

        coords = self._pca_2d(matrix)
        semantic_actions = semantic_actions or [[] for _ in session_ids]
        clusters: list[dict[str, Any]] = []
        for cid in sorted(set(int(x) for x in labels)):
            idxs = [i for i, lab in enumerate(labels) if int(lab) == cid]
            behaviors: dict[str, int] = {}
            for i in idxs:
                for a in semantic_actions[i]:
                    behaviors[a] = behaviors.get(a, 0) + 1
            centroid = matrix[idxs].mean(axis=0).tolist() if idxs else None
            reps = [session_ids[i] for i in idxs[:3]]
            clusters.append(
                {
                    "external_id": int(cid),
                    "size": len(idxs),
                    "common_behaviors": dict(sorted(behaviors.items(), key=lambda x: -x[1])[:8]),
                    "representative_session_ids": reps,
                    "centroid": centroid,
                    "member_indices": idxs,
                }
            )
        return ClusterResult(
            labels=[int(x) for x in labels],
            clusters=clusters,
            coords_2d=coords,
            params={"eps": self.eps, "min_samples": self.min_samples, "algorithm": self.algorithm},
        )

    def _pca_2d(self, matrix: np.ndarray) -> list[list[float]]:
        if matrix.shape[0] < 2 or matrix.shape[1] < 1:
            return [[0.0, 0.0] for _ in range(matrix.shape[0])]
        n = min(2, matrix.shape[0], matrix.shape[1])
        pca = PCA(n_components=n, random_state=42)
        reduced = pca.fit_transform(matrix)
        if n == 1:
            reduced = np.column_stack([reduced, np.zeros(len(reduced))])
        return reduced.tolist()
