from app.agents.kg_builder import run
from app.models.schemas import Paper
from app.orchestrator.state import ResearchState


def _paper(paper_id: str, references: list[str] | None = None) -> Paper:
    return Paper(paper_id=paper_id, title=paper_id, references=references or [])


def test_cites_edge_only_between_retrieved_papers():
    state = ResearchState(question="q")
    state.papers = [
        _paper("s2:a", references=["s2:b", "s2:missing"]),
        _paper("s2:b"),
    ]
    run(state)

    cites_edges = [e for e in state.knowledge_graph.edges if e.type == "cites"]
    assert len(cites_edges) == 1
    assert cites_edges[0].source == "s2:a"
    assert cites_edges[0].target == "s2:b"


def test_no_self_citation_edge():
    state = ResearchState(question="q")
    state.papers = [_paper("s2:a", references=["s2:a"])]
    run(state)

    assert [e for e in state.knowledge_graph.edges if e.type == "cites"] == []


def test_arxiv_papers_have_no_references_so_no_cites_edges():
    state = ResearchState(question="q")
    state.papers = [_paper("arxiv:1"), _paper("arxiv:2")]
    run(state)

    assert [e for e in state.knowledge_graph.edges if e.type == "cites"] == []


def test_hypothesis_hub_links_papers_by_their_stance():
    from app.models.schemas import PaperStance, SubQuestion, VerificationLabel as L

    state = ResearchState(question="q")
    state.sub_questions = [SubQuestion(id="sq1", text="q?", hypothesis="X improves Y.")]
    state.papers = [_paper("a"), _paper("b"), _paper("c")]
    state.paper_stances = [
        PaperStance(paper_id="a", sub_question_id="sq1", label=L.SUPPORTS, confidence=0.9),
        PaperStance(paper_id="b", sub_question_id="sq1", label=L.REFUTES, confidence=0.9),
        PaperStance(paper_id="c", sub_question_id="sq1", label=L.NOT_ENOUGH_INFO, confidence=0.9),
    ]
    run(state)

    hubs = [n for n in state.knowledge_graph.nodes if n.type == "hypothesis"]
    assert [h.label for h in hubs] == ["X improves Y."]
    stance_edges = {(e.source, e.type) for e in state.knowledge_graph.edges if e.target == "hyp_sq1"}
    assert stance_edges == {("a", "supports"), ("b", "contradicts")}  # neutral paper gets no edge
