"""
FAISS Vector DB — semantic memory for long-term context retrieval.
Stores conversation embeddings and retrieves semantically similar past exchanges.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class VectorMemory:
    """
    FAISS-based semantic memory store.
    - Adds user/assistant message pairs as embeddings
    - Retrieves top-K semantically relevant memories
    - Persists index to disk for durability
    """

    EMBEDDING_DIM = 384  # all-MiniLM-L6-v2

    def __init__(self, index_path: str):
        self.index_path = Path(index_path)
        self.meta_path = self.index_path.with_suffix(".json")
        self.index = None
        self.metadata: List[dict] = []  # [{session_id, text, role, timestamp}]
        self._encoder = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Load or create FAISS index and sentence encoder."""
        import faiss  # type: ignore
        from sentence_transformers import SentenceTransformer  # type: ignore
        from app.core.config import settings

        self._encoder = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: SentenceTransformer(settings.FAISS_EMBEDDING_MODEL),
        )

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        index_file = self.index_path.with_suffix(".faiss")

        if index_file.exists() and self.meta_path.exists():
            logger.info("Loading existing FAISS index", path=str(index_file))
            self.index = faiss.read_index(str(index_file))
            with open(self.meta_path) as f:
                self.metadata = json.load(f)
        else:
            logger.info("Creating new FAISS index")
            self.index = faiss.IndexFlatIP(self.EMBEDDING_DIM)  # Inner product (cosine)
            self.metadata = []

    async def add_memory(
        self,
        session_id: str,
        text: str,
        role: str = "user",
    ) -> None:
        """Embed and store a piece of text in FAISS."""
        if not self._encoder or not self.index:
            return

        embedding = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._encoder.encode([text], normalize_embeddings=True),
        )

        async with self._lock:
            self.index.add(embedding.astype(np.float32))
            self.metadata.append({
                "session_id": session_id,
                "text": text,
                "role": role,
                "timestamp": time.time(),
            })
            await self._persist()

    async def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[dict]:
        """Retrieve top-K semantically similar memories."""
        if not self._encoder or not self.index or self.index.ntotal == 0:
            return []

        from app.core.config import settings
        k = min(top_k, self.index.ntotal, settings.FAISS_TOP_K)

        query_emb = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._encoder.encode([query], normalize_embeddings=True),
        )

        scores, indices = self.index.search(query_emb.astype(np.float32), k * 3)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            # Optionally filter by session
            if session_id and meta["session_id"] != session_id:
                continue
            results.append({**meta, "score": float(score)})
            if len(results) >= k:
                break

        return sorted(results, key=lambda x: x["score"], reverse=True)

    async def get_relevant_context(self, query: str, session_id: str) -> str:
        """Return formatted context string from top memories."""
        memories = await self.search(query, session_id=session_id, top_k=3)
        if not memories:
            return ""
        parts = [f"[Memory] {m['role'].title()}: {m['text']}" for m in memories]
        return "\n".join(parts)

    async def _persist(self) -> None:
        """Save FAISS index and metadata to disk."""
        import faiss  # type: ignore
        faiss.write_index(self.index, str(self.index_path.with_suffix(".faiss")))
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)


# ─── Singleton ────────────────────────────────────────────────────────────────
from app.core.config import settings
vector_memory = VectorMemory(settings.FAISS_INDEX_PATH)
