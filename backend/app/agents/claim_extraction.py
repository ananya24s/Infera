"""Claim Extraction agent: pulls atomic, checkable claims out of top-ranked
sources' abstracts. The LLM only helps segment sentences into atomic claims
(a language task); it does not judge whether a claim is true — that's
Verification's job.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid

from app.config import get_settings
from app.models.schemas import Claim, Paper
from app.orchestrator.state import ResearchState
from app.services.llm_client import complete, llm_enabled

logger = logging.getLogger(__name__)

# A local 7B model handles ~2-3 requests at once without thrashing.
_LLM_CONCURRENCY = 3

SYSTEM_PROMPT = (
    "You extract atomic, checkable factual claims from a scientific abstract. "
    "Each claim must be a single self-contained statement (no pronouns needing "
    "outside context, no compound 'X and Y' claims). Use ONLY information stated "
    "in the abstract — never add outside knowledge. Respond ONLY with a JSON "
    "array of strings, each the exact or lightly-cleaned claim text, max 6 items."
)


def _sentence_fallback(abstract: str, max_claims: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", abstract.strip())
    sentences = [s.strip() for s in sentences if len(s.split()) >= 6]
    return sentences[:max_claims]


async def _llm_extract(abstract: str, max_claims: int) -> list[str]:
    raw = await complete(SYSTEM_PROMPT, f"Abstract:\n{abstract}", max_tokens=500)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    items = json.loads(match.group(0) if match else raw)
    cleaned = [str(i).strip() for i in items if str(i).strip()]
    return cleaned[:max_claims] or _sentence_fallback(abstract, max_claims)


def _to_claims(texts: list[str], paper: Paper, sub_question_id: str | None) -> list[Claim]:
    return [
        Claim(
            id=f"c_{uuid.uuid4().hex[:8]}",
            text=text,
            sub_question_id=sub_question_id,
            source_paper_id=paper.paper_id,
            source_sentence=text,
        )
        for text in texts
    ]


async def _llm_extract_all(papers: list[Paper], max_claims: int) -> list[list[str] | None]:
    """One LLM call per paper, a few at a time. A failed call yields None so the
    caller can fall back to plain sentence splitting for just that paper."""
    sem = asyncio.Semaphore(_LLM_CONCURRENCY)

    async def one(paper: Paper) -> list[str] | None:
        async with sem:
            try:
                return await _llm_extract(paper.abstract, max_claims)
            except Exception as exc:  # noqa: BLE001 - LLM is phrasing help only
                logger.warning("claim_extraction: LLM failed for %s (%r); using sentence split", paper.paper_id, exc)
                return None

    return await asyncio.gather(*(one(p) for p in papers))


def run(state: ResearchState) -> None:
    settings = get_settings()
    top_papers = sorted(state.papers, key=lambda p: -p.final_score)[: max(8, len(state.papers) // 2)]
    top_papers = [p for p in top_papers if p.abstract]

    llm_results: list[list[str] | None] = [None] * len(top_papers)
    if top_papers and llm_enabled():
        llm_results = asyncio.run(_llm_extract_all(top_papers, settings.max_claims_per_paper))

    claims: list[Claim] = []
    for paper, texts in zip(top_papers, llm_results):
        if texts is None:
            texts = _sentence_fallback(paper.abstract, settings.max_claims_per_paper)
        sub_question_id = _best_matching_sub_question(paper, state.sub_questions)
        claims.extend(_to_claims(texts, paper, sub_question_id))

    state.claims = claims


def _best_matching_sub_question(paper: Paper, sub_questions) -> str | None:
    if not sub_questions:
        return None
    paper_tokens = set(_tokens(f"{paper.title} {paper.abstract}"))
    best_id, best_overlap = None, -1
    for sq in sub_questions:
        overlap = len(paper_tokens & set(_tokens(sq.text)))
        if overlap > best_overlap:
            best_overlap = overlap
            best_id = sq.id
    return best_id


def _tokens(text: str) -> list[str]:
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if len(t) > 3]
