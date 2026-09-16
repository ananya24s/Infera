"""Stance clustering: groups claims about the same sub-question by semantic
similarity (sentence-transformer embeddings) and separates them by which
NLI verdict they carry, using HDBSCAN for density-based grouping so the
number of stance clusters isn't fixed in advance."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.models.schemas import VerificationLabel


@dataclass
class ClusterInput:
    claim_id: str
    text: str
    label: VerificationLabel


@dataclass
class ClusterResult:
    claim_id: str
    cluster_id: int  # -1 = HDBSCAN noise point (its own singleton cluster)


def cluster_claims(items: list[ClusterInput], min_cluster_size: int = 2) -> list[ClusterResult]:
    if not items:
        return []
    if len(items) < min_cluster_size:
        return [ClusterResult(claim_id=i.claim_id, cluster_id=idx) for idx, i in enumerate(items)]

    from app.services.hybrid_search import _embedder

    embeddings = _embedder().encode(
        [i.text for i in items], normalize_embeddings=True, show_progress_bar=False
    )

    import hdbscan

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size, metric="euclidean", cluster_selection_epsilon=0.15
    )
    labels = clusterer.fit_predict(np.asarray(embeddings, dtype="float64"))

    results = []
    next_singleton = int(labels.max()) + 1 if labels.size else 0
    for item, raw_label in zip(items, labels):
        if raw_label == -1:
            cluster_id = next_singleton
            next_singleton += 1
        else:
            cluster_id = int(raw_label)
        results.append(ClusterResult(claim_id=item.claim_id, cluster_id=cluster_id))
    return results
