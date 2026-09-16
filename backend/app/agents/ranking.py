"""Ranking agent: credibility/relevance scoring via a learned (LightGBM)
ranker over metadata + hybrid-search features. This is the ONLY agent that
decides paper ordering — no LLM opinion involved.
"""
from __future__ import annotations

from app.ml.ranker import features_from_paper, score
from app.orchestrator.state import ResearchState
from app.services.hybrid_search import HybridIndex


def run(state: ResearchState) -> None:
    if not state.papers:
        return

    # Recompute dense/sparse/hybrid features against the *original* question
    # (retrieval scored papers against per-sub-question text) so ranking is
    # consistent across the whole candidate set.
    index = HybridIndex(papers=state.papers)
    scored = {p.paper_id: (d, s, h) for p, d, s, h in index.search(state.question, top_k=len(state.papers))}

    for paper in state.papers:
        dense, sparse, hybrid = scored.get(paper.paper_id, (0.0, 0.0, paper.relevance_score))
        feats = features_from_paper(paper, dense, sparse, hybrid)
        final = score(feats)

        paper.relevance_score = hybrid
        # Credibility leans on citation signal + venue/open-access, independent of query match.
        import math

        credibility = min(
            1.0,
            0.5 * (math.log1p(paper.citation_count) / 10)
            + 0.3 * (math.log1p(paper.influential_citation_count) / 6)
            + 0.2 * (1.0 if paper.is_open_access else 0.0),
        )
        paper.credibility_score = credibility
        paper.final_score = 0.6 * final + 0.4 * credibility

    state.papers.sort(key=lambda p: -p.final_score)
