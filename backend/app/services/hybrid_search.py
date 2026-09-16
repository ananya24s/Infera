"""Hybrid dense + sparse retrieval over an in-memory pool of candidate papers.

Dense side: sentence-transformers embeddings indexed with FAISS (cosine via
normalized inner product). Sparse side: BM25 (rank_bm25) over title+abstract.
Scores are min-max normalized independently and combined with a fixed weight
so neither scale dominates. This module is model inference only — it does not
decide relevance/credibility on its own; RankingAgent consumes its output as
one of several learned-ranker features.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from app.config import get_settings
from app.models.schemas import Paper

_STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "is",
    "are", "was", "were", "with", "that", "this", "by", "as", "at", "be",
    "it", "from", "we", "our",
}


def _tokenize(text: str) -> list[str]:
    return [
        tok
        for tok in "".join(c.lower() if c.isalnum() else " " for c in text).split()
        if tok and tok not in _STOPWORDS
    ]


@lru_cache
def _embedder():
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(settings.embedding_model_name)


@dataclass
class HybridIndex:
    papers: list[Paper]
    dense_weight: float = 0.6

    def __post_init__(self) -> None:
        from rank_bm25 import BM25Okapi

        corpus_text = [f"{p.title} {p.abstract}" for p in self.papers]
        tokenized = [_tokenize(t) for t in corpus_text]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

        if self.papers:
            embeddings = _embedder().encode(
                corpus_text, normalize_embeddings=True, show_progress_bar=False
            )
            self._embeddings = np.asarray(embeddings, dtype="float32")
        else:
            self._embeddings = np.zeros((0, 384), dtype="float32")

        self._index = None
        if len(self.papers) > 0:
            import faiss

            dim = self._embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)
            self._index.add(self._embeddings)

    @staticmethod
    def _min_max(scores: np.ndarray) -> np.ndarray:
        if scores.size == 0:
            return scores
        lo, hi = scores.min(), scores.max()
        if hi - lo < 1e-9:
            return np.zeros_like(scores)
        return (scores - lo) / (hi - lo)

    def search(self, query: str, top_k: int) -> list[tuple[Paper, float, float, float]]:
        """Returns (paper, dense_score, sparse_score, hybrid_score) sorted desc."""
        if not self.papers:
            return []

        bm25_raw = (
            np.asarray(self._bm25.get_scores(_tokenize(query)))
            if self._bm25
            else np.zeros(len(self.papers))
        )
        sparse = self._min_max(bm25_raw)

        query_vec = _embedder().encode([query], normalize_embeddings=True)[0].astype("float32")
        dense_raw = self._embeddings @ query_vec
        dense = self._min_max(dense_raw)

        hybrid = self.dense_weight * dense + (1 - self.dense_weight) * sparse
        order = np.argsort(-hybrid)[:top_k]
        return [
            (self.papers[i], float(dense[i]), float(sparse[i]), float(hybrid[i]))
            for i in order
        ]
