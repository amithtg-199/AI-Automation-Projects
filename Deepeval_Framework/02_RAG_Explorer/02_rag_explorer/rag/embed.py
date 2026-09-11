"""Embeddings via Ollama nomic-embed-text with local deterministic fallback."""
from __future__ import annotations

import os
import hashlib
import math
from typing import Sequence

try:
    import ollama
except ImportError:
    ollama = None

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def _client():
    if ollama is None:
        return None
    return ollama.Client(host=OLLAMA_HOST)


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    if not texts:
        return []

    client = _client()
    if client is not None:
        try:
            out: list[list[float]] = []
            for t in texts:
                resp = client.embeddings(model=EMBED_MODEL, prompt=t)
                out.append(list(resp["embedding"]))
            return out
        except Exception as e:
            print(f"Ollama connection unavailable ({e}), using deterministic embedding fallback")

    # Deterministic fallback embedding generator (384 dimensions)
    return [_fallback_embedding(t) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def model_info() -> dict:
    return {"model": EMBED_MODEL, "host": OLLAMA_HOST}


def _fallback_embedding(text: str, dim: int = 384) -> list[float]:
    vec = [0.0] * dim
    words = text.lower().split()
    for w in words:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]
