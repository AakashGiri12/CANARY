"""Embedding backends for attack_memory retrieval.

Two implementations satisfy the same interface:

- MockEmbedder: deterministic, dependency-free (hashes text into a unit
  vector). Used for local dev/tests on this Intel Mac, which can't
  install sentence-transformers (it pulls in torch, which has no wheels
  here — see the `ml` extra note in pyproject.toml). It's NOT a semantic
  embedding — texts that are merely superficially similar (shared
  substrings) will look similar to it, but genuinely semantically similar
  paraphrases won't necessarily land close together. Good enough to prove
  the retrieval plumbing; not for real similarity judgments.
- MiniLMEmbedder: sentence-transformers/all-MiniLM-L6-v2, the real thing.
  Runs on the Oracle Always Free VM (CPU) per the root CLAUDE.md. Behind
  the `ml` extra; imports lazily so this module loads fine without it.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from attack_engine.db import EMBEDDING_DIM


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class MockEmbedder:
    """Deterministic, dependency-free stand-in. See module docstring."""

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        tokens = text.lower().split()
        if not tokens:
            tokens = [""]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(EMBEDDING_DIM):
                byte = digest[i % len(digest)]
                vector[i] += (byte / 255.0) * 2 - 1  # map to [-1, 1]

        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class MiniLMEmbedder:
    """Real sentence-transformers embedder. Requires the `ml` extra."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # lazy: needs `ml` extra

        self._model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()
