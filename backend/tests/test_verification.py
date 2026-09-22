import app.agents.verification as verification
from app.models.schemas import Claim, Paper, SubQuestion, VerificationLabel as L
from app.orchestrator.state import ResearchState
from tests.conftest import fake_verify_batch

HYPOTHESIS = "Creatine improves cognitive performance."


def _state() -> ResearchState:
    state = ResearchState(question="Does creatine improve cognitive performance?")
    state.sub_questions = [SubQuestion(id="sq1", text="Does creatine improve cognitive performance?", hypothesis=HYPOTHESIS)]
    state.papers = [
        Paper(paper_id="pro", title="Pro", sub_question_id="sq1",
              abstract="Background is discussed at length here. Creatine improved memory scores in adults. Limitations exist too."),
        Paper(paper_id="con", title="Con", sub_question_id="sq1",
              abstract="We ran a trial in students. There was no significant effect on cognition. Sample size was modest."),
        Paper(paper_id="off", title="Off-topic", sub_question_id="sq1",
              abstract="Caffeine intake is widespread among athletes worldwide. Doses vary between sports."),
        Paper(paper_id="none", title="No abstract", sub_question_id="sq1", abstract=""),
    ]
    return state


def _fake_relevance(passages, hypotheses):
    return [0.2 if "regulation" in p.lower() else 0.9 for p in passages]


def _run(monkeypatch, state):
    monkeypatch.setattr(verification, "verify_batch", fake_verify_batch)
    monkeypatch.setattr(verification, "_relevance", _fake_relevance)
    monkeypatch.setattr(verification, "_nearest_sentence", lambda claim, sentences: sentences[0] if sentences else "")
    verification.run(state)


def test_each_paper_gets_a_stance_toward_the_hypothesis(monkeypatch):
    state = _state()
    _run(monkeypatch, state)
    stance = {s.paper_id: s for s in state.paper_stances}

    assert stance["pro"].label == L.SUPPORTS
    assert stance["con"].label == L.REFUTES
    assert stance["off"].label == L.NOT_ENOUGH_INFO
    assert "none" not in stance  # no abstract, nothing to verify


def test_stance_keeps_the_most_decisive_sentence_as_rationale(monkeypatch):
    state = _state()
    _run(monkeypatch, state)
    stance = {s.paper_id: s for s in state.paper_stances}

    assert stance["pro"].evidence_sentence == "Creatine improved memory scores in adults."
    assert stance["con"].evidence_sentence == "There was no significant effect on cognition."
    assert stance["off"].evidence_sentence == ""  # neutral papers have no rationale


def test_claims_get_stance_and_separate_fidelity(monkeypatch):
    state = _state()
    state.claims = [
        Claim(id="c1", text="Creatine improved memory scores.", sub_question_id="sq1", source_paper_id="pro"),
        Claim(id="c2", text="Caffeine intake is widespread.", sub_question_id="sq1", source_paper_id="off"),
    ]
    _run(monkeypatch, state)
    v = {x.claim_id: x for x in state.verdicts}

    assert v["c1"].label == L.SUPPORTS  # the finding supports the hypothesis
    assert v["c2"].label == L.NOT_ENOUGH_INFO  # irrelevant to the hypothesis
    assert v["c1"].fidelity == L.SUPPORTS  # and its own abstract backs it up
    assert v["c1"].evidence_sentence


def test_low_confidence_is_reported_as_not_enough_info(monkeypatch):
    from app.ml.nli_model import NLIResult

    weak = NLIResult(L.SUPPORTS, 0.4, {L.SUPPORTS: 0.4, L.REFUTES: 0.1, L.NOT_ENOUGH_INFO: 0.5})
    monkeypatch.setattr(verification, "verify_batch", lambda pairs: [weak for _ in pairs])
    monkeypatch.setattr(verification, "_relevance", _fake_relevance)
    state = _state()
    verification.run(state)
    assert all(s.label == L.NOT_ENOUGH_INFO for s in state.paper_stances)


def test_off_topic_sentence_cannot_refute_even_if_nli_says_contradiction(monkeypatch):
    state = _state()
    state.papers = [
        Paper(paper_id="risk", title="Supplement risks", sub_question_id="sq1",
              abstract="Supplement regulation did not keep pace with the market. Products vary widely in quality.")
    ]
    _run(monkeypatch, state)
    # The fake NLI reads "did not" as a refutation, but the sentence is off-topic (relevance 0.2).
    assert state.paper_stances[0].label == L.NOT_ENOUGH_INFO
