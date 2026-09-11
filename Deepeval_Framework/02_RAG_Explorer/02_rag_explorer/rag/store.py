"""ChromaDB persistent vector store with in-memory fallback for environments without chromadb."""
from __future__ import annotations

import os
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except Exception:
    chromadb = None
    CHROMADB_AVAILABLE = False

from .ingest import Chunk

DB_DIR = os.getenv("CHROMA_DIR", str(Path(__file__).resolve().parent.parent / "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "ecommerce_kb")


@dataclass
class Hit:
    id: str
    source: str
    text: str
    score: float
    metadata: dict


def _cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1)) or 1e-9
    mag2 = math.sqrt(sum(b * b for b in v2)) or 1e-9
    return dot / (mag1 * mag2)


class VectorStore:
    def __init__(self, path: str = DB_DIR, collection: str = COLLECTION_NAME):
        self.use_chroma = CHROMADB_AVAILABLE
        self.memory_chunks: list[dict] = []
        
        if self.use_chroma:
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
                self.client = chromadb.PersistentClient(
                    path=path,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )
                self.collection = self.client.get_or_create_collection(
                    name=collection,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                print(f"[VectorStore Warning] Failed to initialize ChromaDB ({e}), using in-memory store.")
                self.use_chroma = False

    def reset(self) -> None:
        self.memory_chunks = []
        if self.use_chroma:
            try:
                self.client.delete_collection(self.collection.name)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

    def add_chunks(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> int:
        if not chunks:
            return 0

        if self.use_chroma:
            self.collection.upsert(
                ids=[c.id for c in chunks],
                embeddings=[list(e) for e in embeddings],
                documents=[c.text for c in chunks],
                metadatas=[
                    {
                        "source": c.source,
                        "index": c.index,
                        "char_start": c.char_start,
                        "char_end": c.char_end,
                    }
                    for c in chunks
                ],
            )
        else:
            for c, e in zip(chunks, embeddings):
                self.memory_chunks.append({
                    "id": c.id,
                    "source": c.source,
                    "index": c.index,
                    "text": c.text,
                    "embedding": list(e),
                    "metadata": {
                        "source": c.source,
                        "index": c.index,
                        "char_start": c.char_start,
                        "char_end": c.char_end,
                    }
                })

        return len(chunks)

    def search(self, query_embedding: Sequence[float], top_k: int = 4) -> list[Hit]:
        if self.use_chroma:
            result = self.collection.query(
                query_embeddings=[list(query_embedding)],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
            hits: list[Hit] = []
            if not result["ids"] or not result["ids"][0]:
                return hits
            for hit_id, doc, meta, dist in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            ):
                hits.append(
                    Hit(
                        id=hit_id,
                        source=meta.get("source", "?"),
                        text=doc,
                        score=1.0 - float(dist),
                        metadata=meta,
                    )
                )
            return hits
        else:
            scored = []
            for item in self.memory_chunks:
                sim = _cosine_similarity(query_embedding, item["embedding"])
                scored.append((sim, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            
            hits = []
            for sim, item in scored[:top_k]:
                hits.append(
                    Hit(
                        id=item["id"],
                        source=item["source"],
                        text=item["text"],
                        score=sim,
                        metadata=item["metadata"],
                    )
                )
            return hits

    def stats(self) -> dict[str, Any]:
        if self.use_chroma:
            count = self.collection.count()
            sources: dict[str, int] = {}
            if count > 0:
                sample = self.collection.get(limit=count, include=["metadatas"])
                for m in sample.get("metadatas") or []:
                    src = m.get("source", "?")
                    sources[src] = sources.get(src, 0) + 1
            return {"chunks": count, "sources": sources, "collection": self.collection.name}
        else:
            sources = {}
            for item in self.memory_chunks:
                src = item.get("source", "?")
                sources[src] = sources.get(src, 0) + 1
            return {"chunks": len(self.memory_chunks), "sources": sources, "collection": "in_memory_fallback"}

    def list_chunks(self, source: str | None = None, limit: int = 200) -> list[dict]:
        if self.use_chroma:
            result = self.collection.get(
                limit=limit,
                include=["documents", "metadatas"],
                where={"source": source} if source else None,
            )
            items: list[dict] = []
            for cid, doc, meta in zip(result["ids"], result["documents"], result["metadatas"]):
                items.append({
                    "id": cid,
                    "source": meta.get("source", "?"),
                    "index": meta.get("index", 0),
                    "text": doc,
                    "metadata": meta,
                })
            items.sort(key=lambda x: (x["source"], x["index"]))
            return items
        else:
            items = []
            for item in self.memory_chunks:
                if source and item["source"] != source:
                    continue
                items.append({
                    "id": item["id"],
                    "source": item["source"],
                    "index": item["index"],
                    "text": item["text"],
                    "metadata": item["metadata"],
                })
            items.sort(key=lambda x: (x["source"], x["index"]))
            return items[:limit]
