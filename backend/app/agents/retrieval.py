"""Retrieval agent: hybrid dense+BM25 search over papers pulled live from
Semantic Scholar and arXiv (no fabricated/synthetic papers). For each
sub-question, fetches a candidate pool from both APIs, then runs hybrid
search over the pool to keep the top matches. Papers are deduplicated by
normalized title across sub-questions.
"""
from __future__ import annotations

import asyncio

from app.config import get_settings
from app.models.schemas import Paper
from app.orchestrator.state import ResearchState
from app.services import arxiv, semantic_scholar
from app.services.hybrid_search import HybridIndex


def _norm_title(title: str) -> str:
    return "".join(c.lower() for c in title if c.isalnum())


async def _fetch_pool(query: str, per_source: int) -> list[Paper]:
    results = await asyncio.gather(
        semantic_scholar.search(query, limit=per_source),
        arxiv.search(query, limit=per_source),
        return_exceptions=True,
    )
    pool: list[Paper] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        pool.extend(r)
    return pool


def run(state: ResearchState) -> None:
    settings = get_settings()
    per_sub_question = max(3, state.max_papers // max(len(state.sub_questions), 1))

    seen_titles: dict[str, Paper] = {}
    for sub_q in state.sub_questions:
        pool = asyncio.run(_fetch_pool(sub_q.text, settings.max_retrieval_per_query // 2))
        if not pool:
            continue
        index = HybridIndex(papers=pool)
        top = index.search(sub_q.text, top_k=per_sub_question)
        for paper, dense, sparse, hybrid in top:
            key = _norm_title(paper.title)
            existing = seen_titles.get(key)
            if existing is None or hybrid > existing.relevance_score:
                paper.relevance_score = hybrid
                seen_titles[key] = paper

    state.papers = sorted(seen_titles.values(), key=lambda p: -p.relevance_score)[: state.max_papers]
