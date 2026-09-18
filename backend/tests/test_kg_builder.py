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
