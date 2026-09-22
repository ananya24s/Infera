"""Consensus/Controversy Scoring agent: aggregates per-PAPER stances toward each
sub-question's hypothesis (each source counts once, so a paper with many claims
can't outvote the rest). Pure arithmetic over trained-model outputs — no LLM.

  decisive        papers that took a position (SUPPORTS or REFUTES)
  net_support     (supports - refutes) / decisive         in [-1, 1]
  controversy     1 - |net_support|                       0 = decisive sources
                                                          agree, 1 = split evenly
  evidence        coverage x confidence x sample size     how much decisive,
  strength                                                confident evidence exists
                  coverage    = decisive / all papers
                  confidence  = mean model confidence of the decisive papers
                  sample size = min(1, decisive / 5)      so 1-2 papers can't
                                                          look like strong evidence

A perfectly split literature therefore has HIGH evidence strength and HIGH
controversy — lots of evidence, and it disagrees — which is exactly the
distinction the two scores exist to make.
"""
from __future__ import annotations

from collections import defaultdict

from app.models.schemas import ConsensusScore, PaperStance, VerificationLabel
from app.orchestrator.state import ResearchState

FULL_EVIDENCE_PAPERS = 5
MIXED_CONTROVERSY = 0.5


def score_stances(sub_question_id: str, stances: list[PaperStance]) -> ConsensusScore | None:
    if not stances:
        return None
    supports = sum(1 for s in stances if s.label == VerificationLabel.SUPPORTS)
    refutes = sum(1 for s in stances if s.label == VerificationLabel.REFUTES)
    nei = len(stances) - supports - refutes
    decisive = supports + refutes

    if decisive:
        net = (supports - refutes) / decisive
        controversy = 1 - abs(net)
        decisive_conf = sum(
            s.confidence for s in stances if s.label != VerificationLabel.NOT_ENOUGH_INFO
        ) / decisive
        strength = (decisive / len(stances)) * decisive_conf * min(1.0, decisive / FULL_EVIDENCE_PAPERS)
    else:
        net, controversy, strength = 0.0, 0.0, 0.0

    if decisive < 2:
        verdict = "insufficient"
    elif controversy >= MIXED_CONTROVERSY:
        verdict = "mixed"
    else:
        verdict = "supported" if supports > refutes else "refuted"

    return ConsensusScore(
        sub_question_id=sub_question_id,
        evidence_strength=round(strength, 3),
        controversy_score=round(controversy, 3),
        net_support=round(net, 3),
        verdict=verdict,
        supports=supports,
        refutes=refutes,
        not_enough_info=nei,
    )


def run(state: ResearchState) -> None:
    by_sub_question: dict[str, list[PaperStance]] = defaultdict(list)
    for stance in state.paper_stances:
        by_sub_question[stance.sub_question_id].append(stance)

    scores = []
    for sq in state.sub_questions:
        score = score_stances(sq.id, by_sub_question.get(sq.id, []))
        if score is not None:
            scores.append(score)
    state.consensus = scores
