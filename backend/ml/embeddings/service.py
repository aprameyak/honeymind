from __future__ import annotations

import hashlib
import math
from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    model_name: str
    model_version: str
    dim: int

    def embed(self, text: str) -> list[float]: ...


class HashEmbeddingProvider:
    """Local deterministic embedding for offline lab use (no paid cloud)."""

    def __init__(self, dim: int = 64) -> None:
        self.model_name = "hash"
        self.model_version = "1.0.0"
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float64)
        tokens = text.lower().split()
        if not tokens:
            return vec.tolist()
        for i, tok in enumerate(tokens):
            h = hashlib.sha256(tok.encode()).digest()
            idx = int.from_bytes(h[:4], "big") % self.dim
            sign = 1.0 if h[4] % 2 == 0 else -1.0
            vec[idx] += sign * (1.0 + (i % 5) * 0.1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        self.provider = provider or HashEmbeddingProvider()

    def embed_action(self, action: str) -> list[float]:
        return self.provider.embed(action)

    def embed_session(self, summary: str) -> list[float]:
        return self.provider.embed(summary)

    def hybrid(self, embedding: list[float], behavioral: list[float], emb_k: int = 32) -> list[float]:
        emb = embedding[:emb_k]
        if len(emb) < emb_k:
            emb = emb + [0.0] * (emb_k - len(emb))
        return emb + behavioral
