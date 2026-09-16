from app.agents.consensus_scoring import run
from app.models.schemas import Claim, Verdict, VerificationLabel
from app.orchestrator.state import ResearchState


def _state_with(labels: list[VerificationLabel]) -> ResearchState:
    state = ResearchState(question="does X cause Y?")
    for i, label in enumerate(labels):
        claim = Claim(id=f"c{i}", text=f"claim {i}", sub_question_id="sq1", source_paper_id=f"p{i}")
        state.claims.append(claim)
        state.verdicts.append(Verdict(claim_id=claim.id, label=label, confidence=0.9))
    return state


def test_unanimous_support_gives_low_controversy_high_strength():
    state = _state_with([VerificationLabel.SUPPORTS] * 5)
    run(state)
    assert len(state.consensus) == 1
    cs = state.consensus[0]
    assert cs.controversy_score == 0.0
    assert cs.evidence_strength > 0.8


def test_even_split_gives_max_controversy():
    state = _state_with([VerificationLabel.SUPPORTS, VerificationLabel.REFUTES])
    run(state)
    cs = state.consensus[0]
    assert cs.controversy_score == 1.0


def test_all_not_enough_info_gives_zero_controversy_and_strength():
    state = _state_with([VerificationLabel.NOT_ENOUGH_INFO] * 3)
    run(state)
    cs = state.consensus[0]
    assert cs.controversy_score == 0.0
    assert cs.evidence_strength == 0.0
