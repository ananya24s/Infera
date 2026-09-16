"""Claim Extraction agent: pulls atomic, checkable claims out of top-ranked
sources' abstracts. The LLM only helps segment sentences into atomic claims
(a language task); it does not judge whether a claim is true — that's
Verification's job.
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid

from app.config import get_settings
from app.models.schemas import Claim, Paper
from app.orchestrator.state import ResearchState
from app.services.llm_client import complete, llm_enabled

SYSTEM_PROMPT = (
    "You extract atomic, checkable factual claims from a scientific abstract. "
    "Each claim must be a single self-contained statement (no pronouns needing "
    "outside context, no compound 'X and Y' claims). Respond ONLY with a JSON "
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


def _extract_for_paper(paper: Paper, sub_question_id: str | None, max_claims: int) -> list[Claim]:
    if not paper.abstract:
        return []
    if llm_enabled():
        texts = asyncio.run(_llm_extract(paper.abstract, max_claims))
    else:
        texts = _sentence_fallback(paper.abstract, max_claims)

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


def run(state: ResearchState) -> None:
    settings = get_settings()
    top_papers = sorted(state.papers, key=lambda p: -p.final_score)[: max(8, len(state.papers) // 2)]

    claims: list[Claim] = []
    for paper in top_papers:
        sub_question_id = _best_matching_sub_question(paper, state.sub_questions)
        claims.extend(_extract_for_paper(paper, sub_question_id, settings.max_claims_per_paper))

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
