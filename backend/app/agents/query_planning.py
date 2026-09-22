"""Query Planning agent: splits the research question into sub-questions and
turns each into a declarative *hypothesis* that sources are verified against.

Uses the LLM for phrasing when available (decomposing a question and
restating it as a statement are language tasks), with rule-based fallbacks so
the pipeline still runs without one.
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
    "You split a research question into 1-5 focused, independently-searchable "
    "sub-questions that together cover the original question (use just one if the "
    "question is already focused). For each, also write its 'hypothesis': the "
    "sub-question restated as a single declarative statement that a study could "
    "support or refute, e.g. 'Does creatine improve memory?' -> 'Creatine improves "
    "memory.' Respond ONLY with a JSON array of objects: "
    '[{"text": ..., "hypothesis": ..., "rationale": ...}]. No prose.'
)

# Verbs that commonly head a research question; used to conjugate "Does X <verb> Y?"
# into "X <verb>s Y." when no LLM is available.
_RESEARCH_VERBS = {
    "improve", "reduce", "increase", "decrease", "cause", "prevent", "affect", "impair",
    "lower", "raise", "help", "lead", "enhance", "boost", "promote", "protect", "worsen",
    "treat", "cure", "trigger", "predict", "influence", "alter", "delay", "accelerate",
    "slow", "stop", "induce", "inhibit", "stimulate", "support", "harm", "damage",
    "extend", "shorten", "mitigate", "moderate", "modify", "change", "hinder", "benefit",
}
_PREDICATE_ADJECTIVES = {
    "effective", "safe", "better", "worse", "harmful", "beneficial", "useful", "necessary",
    "sufficient", "associated", "linked", "related", "superior", "inferior", "dangerous",
    "helpful", "ineffective", "efficient", "common", "important", "responsible", "different",
}


def _conjugate(verb: str) -> str:
    if verb.endswith(("s", "sh", "ch", "x", "z")):
        return verb + "es"
    if verb.endswith("y") and verb[-2:-1] not in "aeiou":
        return verb[:-1] + "ies"
    return verb + "s"


def question_to_hypothesis(question: str) -> str:
    """Best-effort rule-based restatement of a yes/no question as a statement.
    Falls back to the question text without its '?' when the shape isn't recognised."""
    q = question.strip().rstrip("?").strip()
    words = q.split()
    if len(words) < 3:
        return q
    aux, rest = words[0].lower(), words[1:]

    if aux in {"does", "do", "did"}:
        for i, w in enumerate(rest):
            if w.lower() in _RESEARCH_VERBS and i > 0:
                verb = _conjugate(w.lower()) if aux == "does" else w.lower()
                stmt = " ".join(rest[:i] + [verb] + rest[i + 1:])
                return stmt[0].upper() + stmt[1:] + "."
    elif aux in {"is", "are", "was", "were"}:
        for i, w in enumerate(rest):
            comparative = i + 1 < len(rest) and rest[i + 1].lower() == "than"
            if (w.lower() in _PREDICATE_ADJECTIVES or comparative) and i > 0:
                stmt = " ".join(rest[:i] + [aux] + rest[i:])
                return stmt[0].upper() + stmt[1:] + "."
    elif aux in {"can", "could", "will", "would", "should", "may", "might"} and len(rest) >= 2:
        stmt = " ".join([rest[0], aux] + rest[1:])
        return stmt[0].upper() + stmt[1:] + "."

    return q if q.endswith(".") else q + "."


def _fallback_split(question: str, max_sub_questions: int) -> list[SubQuestion]:
    clauses = re.split(r";| and (?=\w+ ?\w* (does|is|are|can|has))", question, flags=re.IGNORECASE)
    clauses = [c.strip(" ?.") for c in clauses if c and c.strip(" ?.")]
    if not clauses:
        clauses = [question]
    clauses = clauses[:max_sub_questions] or [question]
    subs = []
    for i, c in enumerate(clauses):
        text = c if c.endswith("?") else f"{c}?"
        subs.append(
            SubQuestion(
                id=f"sq{i+1}",
                text=text,
                hypothesis=question_to_hypothesis(text),
                rationale="rule-based split",
            )
        )
    return subs


async def _llm_split(question: str, max_sub_questions: int) -> list[SubQuestion]:
    prompt = f'Research question: "{question}"\nMax sub-questions: {max_sub_questions}'
    raw = await complete(SYSTEM_PROMPT, prompt, max_tokens=700)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    items = json.loads(match.group(0) if match else raw)
    subs = []
    for i, item in enumerate(items[:max_sub_questions]):
        text = str(item["text"]).strip()
        hypothesis = str(item.get("hypothesis") or "").strip() or question_to_hypothesis(text)
        subs.append(
            SubQuestion(id=f"sq{i+1}", text=text, hypothesis=hypothesis, rationale=str(item.get("rationale", "")))
        )
    return subs or _fallback_split(question, max_sub_questions)


def run(state: ResearchState) -> None:
    if llm_enabled():
        try:
            state.sub_questions = asyncio.run(_llm_split(state.question, state.max_sub_questions))
            return
        except Exception as exc:  # noqa: BLE001 - LLM is phrasing help only; never fail the query over it
            logger.warning("query_planning: LLM split failed (%r); using rule-based split", exc)
    state.sub_questions = _fallback_split(state.question, state.max_sub_questions)
