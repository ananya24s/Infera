"""Report Generation agent.

Drafts prose with the LLM (phrasing only), grounded in the consensus scores
and claim verdicts already computed — the LLM is instructed to write only
what the evidence supports. It then self-checks: each declarative sentence
in the draft is re-run through the same NLI model against the pooled
evidence for its sub-question. Sentences that come back REFUTES or
NOT_ENOUGH_INFO are flagged and the LLM is asked to revise just those
sentences (still phrasing-only) using the actual evidence text. Falls back
to a template report (no LLM) when no API key is configured.
"""
from __future__ import annotations

import asyncio
import re

from app.models.schemas import ResearchReport, VerificationLabel
from app.ml.nli_model import verify
from app.orchestrator.state import ResearchState
from app.services.llm_client import complete, llm_enabled

DRAFT_SYSTEM_PROMPT = (
    "You are a scientific research assistant writing a short evidence report. "
    "You will be given, per sub-question, an evidence-strength score, a "
    "controversy score, counts of SUPPORTS/REFUTES/NOT_ENOUGH_INFO verdicts, "
    "and the actual claim texts with their verdicts. Write ONLY what the "
    "evidence supports — do not add outside knowledge or hedge-free claims "
    "beyond what's given. Structure: one short overall summary paragraph, then "
    "one paragraph per sub-question citing the balance of evidence in plain "
    "English (e.g. 'evidence is mixed', 'most sources agree that...'). Output "
    "markdown with a top-level '## Summary' and '## <sub-question>' sections."
)

REVISE_SYSTEM_PROMPT = (
    "You are revising specific sentences in a scientific evidence report that "
    "were found to be unsupported or contradicted by the underlying evidence. "
    "For each flagged sentence you are given the sentence, why it failed "
    "(REFUTES or NOT_ENOUGH_INFO), and the actual supporting evidence texts. "
    "Rewrite ONLY that sentence so it accurately reflects the evidence "
    "(including saying evidence is mixed/insufficient if that's the truth). "
    "Respond with a JSON array of {\"original\": ..., \"revised\": ...}."
)


def _evidence_context(state: ResearchState) -> str:
    lines = []
    for cs in state.consensus:
        sq = next((s for s in state.sub_questions if s.id == cs.sub_question_id), None)
        topic = sq.text if sq else cs.sub_question_id
        lines.append(
            f"\n### {topic}\nevidence_strength={cs.evidence_strength} "
            f"controversy={cs.controversy_score} supports={cs.supports} "
            f"refutes={cs.refutes} not_enough_info={cs.not_enough_info}"
        )
        for claim in state.claims:
            if claim.sub_question_id != cs.sub_question_id:
                continue
            v = state.verdict_by_claim(claim.id)
            if v:
                lines.append(f"- [{v.label.value}] {claim.text}")
    return "\n".join(lines)


def _template_report(state: ResearchState) -> ResearchReport:
    parts = [f"## Summary\nEvidence gathered for: *{state.question}*\n"]
    for cs in state.consensus:
        sq = next((s for s in state.sub_questions if s.id == cs.sub_question_id), None)
        topic = sq.text if sq else cs.sub_question_id
        verdict_word = (
            "strong support" if cs.evidence_strength > 0.66
            else "mixed/weak support" if cs.evidence_strength > 0.33
            else "little to no support"
        )
        parts.append(
            f"## {topic}\nEvidence shows {verdict_word} "
            f"(supports={cs.supports}, refutes={cs.refutes}, "
            f"not_enough_info={cs.not_enough_info}, controversy={cs.controversy_score})."
        )
    body = "\n\n".join(parts)
    return ResearchReport(question=state.question, summary=parts[0], body_markdown=body)


def _split_sentences(markdown: str) -> list[str]:
    plain = re.sub(r"^#+.*$", "", markdown, flags=re.MULTILINE)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if len(s.split()) >= 5]


def _pooled_evidence_for(state: ResearchState, sub_question_id: str | None) -> str:
    texts = [
        c.text
        for c in state.claims
        if c.sub_question_id == sub_question_id and state.verdict_by_claim(c.id)
    ]
    return " ".join(texts)


def _closest_sub_question(state: ResearchState, sentence: str) -> str | None:
    tokens = set(re.findall(r"[a-z]{4,}", sentence.lower()))
    best_id, best_overlap = None, -1
    for sq in state.sub_questions:
        overlap = len(tokens & set(re.findall(r"[a-z]{4,}", sq.text.lower())))
        if overlap > best_overlap:
            best_overlap, best_id = overlap, sq.id
    return best_id


async def _self_check_and_revise(state: ResearchState, draft: str) -> tuple[str, bool, list[str]]:
    sentences = _split_sentences(draft)
    flagged = []
    for sentence in sentences:
        sub_q_id = _closest_sub_question(state, sentence)
        pooled_evidence = _pooled_evidence_for(state, sub_q_id)
        if not pooled_evidence:
            continue
        result = verify(premise=pooled_evidence, hypothesis=sentence)
        if result.label != VerificationLabel.SUPPORTS:
            flagged.append(
                {
                    "original": sentence,
                    "reason": result.label.value,
                    "evidence": pooled_evidence[:1000],
                }
            )

    if not flagged:
        return draft, False, []

    if not llm_enabled():
        notes = [f"Flagged (not auto-revised, no LLM configured): {f['original']}" for f in flagged]
        return draft, True, notes

    import json

    prompt = json.dumps(flagged, indent=2)
    raw = await complete(REVISE_SYSTEM_PROMPT, prompt, max_tokens=800)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    revisions = json.loads(match.group(0)) if match else []

    revised_draft = draft
    notes = []
    for r in revisions:
        original, revised = r.get("original", ""), r.get("revised", "")
        if original and revised and original in revised_draft:
            revised_draft = revised_draft.replace(original, revised)
            notes.append(f"Revised: \"{original}\" -> \"{revised}\"")

    return revised_draft, True, notes


async def _generate(state: ResearchState) -> ResearchReport:
    context = _evidence_context(state)
    draft = await complete(
        DRAFT_SYSTEM_PROMPT,
        f'Research question: "{state.question}"\n\nEvidence:\n{context}',
        max_tokens=1500,
    )
    final_body, revised, notes = await _self_check_and_revise(state, draft)
    summary = final_body.split("## ", 2)[1] if "## " in final_body else final_body[:300]

    return ResearchReport(
        question=state.question,
        summary=summary.strip()[:500],
        body_markdown=final_body,
        revised=revised,
        revision_notes=notes,
    )


def run(state: ResearchState) -> None:
    if llm_enabled():
        state.report = asyncio.run(_generate(state))
    else:
        state.report = _template_report(state)
