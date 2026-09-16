"""Learned relevance/credibility ranker.

Feature vector per (query, paper) pair:
  dense_score, sparse_score, hybrid_score, log1p(citation_count),
  log1p(influential_citation_count), is_open_access, recency (1 / (1 + years_old))

Ranking is a LightGBM regressor predicting a combined 0-1 score. Train it with
backend/training/train_ranker.py against real judged (query, paper, label)
triples (e.g. citation-graph-derived relevance labels) — never hand-fabricated
data. Until a trained model exists at INFERA_RANKER_PATH, `score()` falls back
to a transparent, fixed-weight linear combination of the same features so the
pipeline still runs end-to-end; the moment a checkpoint is trained, it's used
automatically with no code changes.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import numpy as np

from app.config import get_settings
from app.models.schemas import Paper

FEATURE_NAMES = [
    "dense_score",
    "sparse_score",
    "hybrid_score",
    "log_citations",
    "log_influential_citations",
    "is_open_access",
    "recency",
]

# Fallback weights used only when no trained LightGBM checkpoint is available.
_FALLBACK_WEIGHTS = np.array([0.30, 0.15, 0.25, 0.12, 0.08, 0.04, 0.06])


@dataclass
class RankFeatures:
    dense_score: float
    sparse_score: float
    hybrid_score: float
    citation_count: int
    influential_citation_count: int
    is_open_access: bool
    year: int | None

    def to_vector(self) -> np.ndarray:
        current_year = date.today().year
        years_old = max(current_year - self.year, 0) if self.year else 15
        return np.array(
            [
                self.dense_score,
                self.sparse_score,
                self.hybrid_score,
                math.log1p(self.citation_count),
                math.log1p(self.influential_citation_count),
                1.0 if self.is_open_access else 0.0,
                1.0 / (1.0 + years_old),
            ]
        )


@lru_cache
def _booster():
    settings = get_settings()
    if not os.path.exists(settings.ranker_model_path):
        return None
    import lightgbm as lgb

    return lgb.Booster(model_file=settings.ranker_model_path)


def score(features: RankFeatures) -> float:
    vec = features.to_vector()
    booster = _booster()
    if booster is not None:
        return float(booster.predict(vec.reshape(1, -1))[0])
    # Fallback: normalized linear score, clipped to [0, 1].
    raw = float(np.dot(vec, _FALLBACK_WEIGHTS))
    return max(0.0, min(1.0, raw))


def features_from_paper(paper: Paper, dense: float, sparse: float, hybrid: float) -> RankFeatures:
    return RankFeatures(
        dense_score=dense,
        sparse_score=sparse,
        hybrid_score=hybrid,
        citation_count=paper.citation_count,
        influential_citation_count=paper.influential_citation_count,
        is_open_access=paper.is_open_access,
        year=paper.year,
    )
