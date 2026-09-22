import app.agents.report_generation as rg
from app.models.schemas import ConsensusScore, Paper, PaperStance, SubQuestion, VerificationLabel as L
from app.orchestrator.state import ResearchState
from tests.conftest import fake_verify_batch


def _state() -> ResearchState:
    state = ResearchState(question="Does creatine improve cognitive performance?")
    state.sub_questions = [SubQuestion(id="sq1", text="q?", hypothesis="Creatine improves cognitive performance.")]
    state.papers = [
        Paper(paper_id="pro", title="Creatine and memory", year=2012, url="https://x/1", abstract="Creatine improved memory scores in adults."),
        Paper(paper_id="con", title="Creatine null result", year=2019, abstract="There was no significant effect on cognition."),
    ]
    state.paper_stances = [
        PaperStance(paper_id="pro", sub_question_id="sq1", label=L.SUPPORTS, confidence=0.93,
                    evidence_sentence="Creatine improved memory scores in adults."),
        PaperStance(paper_id="con", sub_question_id="sq1", label=L.REFUTES, confidence=0.95,
                    evidence_sentence="There was no significant effect on cognition."),
    ]
    state.consensus = [ConsensusScore(sub_question_id="sq1", evidence_strength=0.4, controversy_score=1.0,
                                      net_support=0.0, verdict="mixed", supports=1, refutes=1, not_enough_info=0)]
    return state


def test_template_report_lists_both_sides_with_numbered_sources():
    state = _state()
    sections, by_number = rg._plan(state)
    report = rg._template_report(state, sections, by_number)

    assert report.generated_by == "template"
    assert "Verdict: **mixed**" in report.body_markdown
    assert "Supporting evidence" in report.body_markdown and "Contradicting evidence" in report.body_markdown
    assert "## Sources" in report.body_markdown
    assert "[1] Creatine and memory (2012)" in report.body_markdown


def test_citation_check_flags_a_sentence_its_source_does_not_support(monkeypatch):
    monkeypatch.setattr(rg, "verify_batch", fake_verify_batch)
    monkeypatch.setattr(rg, "_premise_for", lambda cited, sentence: cited.paper.abstract)
    _, by_number = rg._plan(_state())

    draft = (
        "## Summary\nThe evidence is mixed.\n\n"
        "## Creatine improves cognitive performance.\n"
        "One trial found improved memory in adults [1]. "
        "Another trial found large gains in every domain [2]."
    )
    checked, flags = rg._check_citations(draft, by_number)

    assert checked == 2
    assert [f.n for f in flags] == [2]  # [2]'s source says "no significant effect"
    assert flags[0].label == L.REFUTES


def test_uncited_summary_sentences_are_not_checked(monkeypatch):
    monkeypatch.setattr(rg, "verify_batch", fake_verify_batch)
    _, by_number = rg._plan(_state())
    checked, flags = rg._check_citations("## Summary\nOverall the evidence looks mixed at this point.", by_number)
    assert checked == 0 and flags == []


def test_multi_citation_aggregate_sentences_are_not_checked_source_by_source(monkeypatch):
    monkeypatch.setattr(rg, "verify_batch", fake_verify_batch)
    monkeypatch.setattr(rg, "_premise_for", lambda cited, sentence: cited.paper.abstract)
    _, by_number = rg._plan(_state())

    # Accurate, but no single source entails it — must not be flagged or removed.
    draft = "## Summary\nOne study supports the hypothesis [1], while another refutes it [2]."
    checked, flags = rg._check_citations(draft, by_number)
    assert checked == 0 and flags == []


def test_llm_report_gets_a_code_written_consensus_block():
    sections, _ = rg._plan(_state())
    block = rg._consensus_block(sections)
    assert block.startswith("## Consensus") and "Verdict: **mixed**" in block


def test_revision_tolerates_a_model_that_returns_bare_strings(monkeypatch):
    import asyncio

    async def fake_complete(system, prompt, max_tokens=0):
        return '["Rewrote the sentence", "another string"]'  # not the requested objects

    monkeypatch.setattr(rg, "complete", fake_complete)
    _, by_number = rg._plan(_state())
    flag = rg._Flag("A claim [1].", 1, L.NOT_ENOUGH_INFO, 0.9, "premise")

    body, notes = asyncio.run(rg._revise("A claim [1].", [flag], by_number))
    assert body == "A claim [1]."  # draft kept untouched, no crash


def test_check_judges_content_not_list_markers_or_the_sources_own_title(monkeypatch):
    seen: list[tuple[str, str]] = []

    def spy(pairs):
        seen.extend(pairs)
        return fake_verify_batch(pairs)

    monkeypatch.setattr(rg, "verify_batch", spy)
    monkeypatch.setattr(rg, "_premise_for", lambda cited, claim: cited.paper.abstract)
    _, by_number = rg._plan(_state())

    draft = (
        "## Creatine improves cognitive performance.\n"
        "1. [1] Creatine and memory (2012) found that creatine improved memory in adults.\n"
        "2. Another study reported large gains in every domain [2].\n"
    )
    checked, flags = rg._check_citations(draft, by_number)

    assert checked == 2
    claims = [claim for _premise, claim in seen]
    assert claims[0] == "found that creatine improved memory in adults."
    assert all("Creatine and memory" not in c and not c.lstrip().startswith(("1.", "2.")) for c in claims)
    assert [f.n for f in flags] == [2]
