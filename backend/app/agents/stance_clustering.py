"""Stance Clustering agent: groups claims (within each sub-question) by
semantic similarity + verdict label using HDBSCAN, so we can see where
sources actually agree/disagree rather than just averaging labels.
"""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict

from app.models.schemas import StanceCluster
from app.ml.clustering import ClusterInput, cluster_claims
from app.orchestrator.state import ResearchState


def run(state: ResearchState) -> None:
    by_sub_question: dict[str | None, list] = defaultdict(list)
    for claim in state.claims:
        verdict = state.verdict_by_claim(claim.id)
        if verdict is None:
            continue
        by_sub_question[claim.sub_question_id].append((claim, verdict))

    clusters: list[StanceCluster] = []
    for sub_question_id, claim_verdicts in by_sub_question.items():
        inputs = [
            ClusterInput(claim_id=c.id, text=c.text, label=v.label) for c, v in claim_verdicts
        ]
        results = cluster_claims(inputs)
        cluster_id_to_claim_ids: dict[int, list[str]] = defaultdict(list)
        for r in results:
            cluster_id_to_claim_ids[r.cluster_id].append(r.claim_id)

        label_by_claim = {c.id: v.label for c, v in claim_verdicts}
        topic = next(
            (sq.text for sq in state.sub_questions if sq.id == sub_question_id),
            state.question,
        )

        for local_id, claim_ids in cluster_id_to_claim_ids.items():
            labels = [label_by_claim[cid] for cid in claim_ids]
            dominant_label, dominant_count = Counter(labels).most_common(1)[0]
            clusters.append(
                StanceCluster(
                    id=f"cl_{uuid.uuid4().hex[:8]}",
                    topic=topic,
                    claim_ids=claim_ids,
                    dominant_label=dominant_label,
                    agreement_ratio=dominant_count / len(labels),
                )
            )

    state.clusters = clusters
