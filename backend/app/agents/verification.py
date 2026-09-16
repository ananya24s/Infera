"""Verification agent: labels each claim SUPPORTS/REFUTES/NOT_ENOUGH_INFO
against its source paper's abstract using a fine-tuned NLI model (see
app/ml/nli_model.py). This is a trained-model judgment, not an LLM opinion.
"""
from __future__ import annotations

from app.models.schemas import Verdict
from app.ml.nli_model import verify
from app.orchestrator.state import ResearchState


def run(state: ResearchState) -> None:
    verdicts: list[Verdict] = []
    for claim in state.claims:
        paper = state.paper_by_id(claim.source_paper_id)
        premise = paper.abstract if paper else claim.source_sentence
        result = verify(premise=premise, hypothesis=claim.text)
        verdicts.append(
            Verdict(
                claim_id=claim.id,
                label=result.label,
                confidence=result.confidence,
                evidence_sentence=claim.source_sentence,
            )
        )
    state.verdicts = verdicts
