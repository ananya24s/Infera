"""Consensus/Controversy Scoring agent: aggregates NLI verdicts per
sub-question into an evidence-strength score (how much support exists, and
how strong) and a controversy score (how split the evidence is). Pure
arithmetic over trained-model outputs — no LLM involved.
"""
from __future__ import annotations

from collections import defaultdict

from app.models.schemas import ConsensusScore, VerificationLabel
from app.orchestrator.state import ResearchState


def run(state: ResearchState) -> None:
    by_sub_question: dict[str, list] = defaultdict(list)
    for claim in state.claims:
        if not claim.sub_question_id:
            continue
        verdict = state.verdict_by_claim(claim.id)
        if verdict is not None:
            by_sub_question[claim.sub_question_id].append(verdict)

    scores: list[ConsensusScore] = []
    for sub_question_id, verdicts in by_sub_question.items():
        supports = sum(1 for v in verdicts if v.label == VerificationLabel.SUPPORTS)
        refutes = sum(1 for v in verdicts if v.label == VerificationLabel.REFUTES)
        nei = sum(1 for v in verdicts if v.label == VerificationLabel.NOT_ENOUGH_INFO)
        total = len(verdicts)
        if total == 0:
            continue

        # Evidence strength: net directional support, confidence-weighted, scaled to [0, 1].
        avg_conf = sum(v.confidence for v in verdicts) / total
        directional = (supports - refutes) / total  # in [-1, 1]
        evidence_strength = max(0.0, (directional + 1) / 2 * avg_conf + (1 - avg_conf) * 0.5)
        evidence_strength = min(1.0, evidence_strength) if (supports + refutes) else 0.0

        # Controversy: entropy-like measure over the supports/refutes split
        # (ignoring NEI, since "no evidence" isn't "disagreement").
        decisive = supports + refutes
        if decisive == 0:
            controversy = 0.0
        else:
            p_support = supports / decisive
            p_refute = refutes / decisive
            controversy = 1 - abs(p_support - p_refute)  # 1.0 = perfectly split, 0.0 = unanimous

        scores.append(
            ConsensusScore(
                sub_question_id=sub_question_id,
                evidence_strength=round(evidence_strength, 3),
                controversy_score=round(controversy, 3),
                supports=supports,
                refutes=refutes,
                not_enough_info=nei,
            )
        )

    state.consensus = scores
