"""Query Planning agent: splits the research question into sub-questions.

Uses the LLM for phrasing when available (it's genuinely a language task —
decomposing a question into readable sub-questions), with a rule-based
fallback (the question itself, plus any explicit "and"/";" clauses) so the
pipeline still runs without an API key.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from app.models.schemas import SubQuestion
from app.orchestrator.state import ResearchState
from app.services.llm_client import complete, llm_enabled

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You split a research question into 2-5 focused, independently-searchable "
    "sub-questions that together cover the original question. Respond ONLY with "
    "a JSON array of objects: [{\"text\": ..., \"rationale\": ...}]. No prose."
)


def _fallback_split(question: str, max_sub_questions: int) -> list[SubQuestion]:
    clauses = re.split(r";| and (?=\w+ ?\w* (does|is|are|can|has))", question, flags=re.IGNORECASE)
    clauses = [c.strip(" ?.") for c in clauses if c and c.strip(" ?.")]
    if not clauses:
        clauses = [question]
    clauses = clauses[:max_sub_questions] or [question]
    return [
        SubQuestion(id=f"sq{i+1}", text=c if c.endswith("?") else f"{c}?", rationale="rule-based split")
        for i, c in enumerate(clauses)
    ]


async def _llm_split(question: str, max_sub_questions: int) -> list[SubQuestion]:
    prompt = f'Research question: "{question}"\nMax sub-questions: {max_sub_questions}'
    raw = await complete(SYSTEM_PROMPT, prompt, max_tokens=600)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    items = json.loads(match.group(0) if match else raw)
    subs = [
        SubQuestion(id=f"sq{i+1}", text=item["text"], rationale=item.get("rationale", ""))
        for i, item in enumerate(items[:max_sub_questions])
    ]
    return subs or _fallback_split(question, max_sub_questions)


def run(state: ResearchState) -> None:
    if llm_enabled():
        try:
            state.sub_questions = asyncio.run(_llm_split(state.question, state.max_sub_questions))
            return
        except Exception as exc:  # noqa: BLE001 - LLM is phrasing help only; never fail the query over it
            logger.warning("query_planning: LLM split failed (%r); using rule-based split", exc)
    state.sub_questions = _fallback_split(state.question, state.max_sub_questions)
