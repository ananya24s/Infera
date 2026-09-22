from app.agents.consensus_scoring import run, score_stances
from app.models.schemas import PaperStance, SubQuestion, VerificationLabel as L
from app.orchestrator.state import ResearchState


def _stances(labels: list[L], conf: float = 0.9) -> list[PaperStance]:
    return [PaperStance(paper_id=f"p{i}", sub_question_id="sq1", label=l, confidence=conf) for i, l in enumerate(labels)]


def test_unanimous_support_is_supported_with_no_controversy():
    cs = score_stances("sq1", _stances([L.SUPPORTS] * 6))
    assert cs.verdict == "supported"
    assert cs.controversy_score == 0.0
    assert cs.net_support == 1.0
    assert cs.evidence_strength > 0.8


def test_even_split_is_mixed_with_max_controversy_but_strong_evidence():
    cs = score_stances("sq1", _stances([L.SUPPORTS] * 3 + [L.REFUTES] * 3))
    assert cs.verdict == "mixed"
    assert cs.controversy_score == 1.0
    assert cs.net_support == 0.0
    # lots of decisive evidence that disagrees: strong evidence AND high controversy
    assert cs.evidence_strength > 0.8


def test_majority_refute_is_refuted():
    cs = score_stances("sq1", _stances([L.REFUTES] * 7 + [L.SUPPORTS]))
    assert cs.verdict == "refuted"
    assert cs.net_support < 0


def test_all_neutral_is_insufficient_with_zero_strength():
    cs = score_stances("sq1", _stances([L.NOT_ENOUGH_INFO] * 4))
    assert cs.verdict == "insufficient"
    assert cs.evidence_strength == 0.0 and cs.controversy_score == 0.0


def test_one_confident_paper_is_not_strong_evidence():
    cs = score_stances("sq1", _stances([L.SUPPORTS] + [L.NOT_ENOUGH_INFO] * 4))
    assert cs.verdict == "insufficient"  # a single paper can't establish a consensus
    assert cs.evidence_strength < 0.25


def test_neutral_papers_lower_evidence_strength_not_controversy():
    few = score_stances("sq1", _stances([L.SUPPORTS] * 5 + [L.NOT_ENOUGH_INFO] * 15))
    many = score_stances("sq1", _stances([L.SUPPORTS] * 5))
    assert few.controversy_score == many.controversy_score == 0.0
    assert few.evidence_strength < many.evidence_strength


def test_run_scores_each_sub_question_from_paper_stances():
    state = ResearchState(question="q")
    state.sub_questions = [SubQuestion(id="sq1", text="a?"), SubQuestion(id="sq2", text="b?")]
    state.paper_stances = _stances([L.SUPPORTS, L.SUPPORTS])
    run(state)
    assert [c.sub_question_id for c in state.consensus] == ["sq1"]  # sq2 has no stances
