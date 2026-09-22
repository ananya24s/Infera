"""Knowledge Graph Builder agent, derived entirely from retrieval + verification
output (no LLM-invented edges).

Nodes:  hypothesis (one per sub-question) · paper · claim
Edges:  paper --supports/contradicts--> hypothesis   (the paper's NLI stance)
        paper --cites--> paper                        (only between retrieved papers)
        claim --extracted_from--> paper

Papers that take no position (NOT_ENOUGH_INFO) get no stance edge; they stay
connected through their claims and citations.
"""
from __future__ import annotations

from app.models.schemas import KGEdge, KGNode, KnowledgeGraph, VerificationLabel
from app.orchestrator.state import ResearchState

_STANCE_EDGE = {
    VerificationLabel.SUPPORTS: "supports",
    VerificationLabel.REFUTES: "contradicts",
}


def run(state: ResearchState) -> None:
    nodes: list[KGNode] = []
    edges: list[KGEdge] = []

    consensus = {c.sub_question_id: c for c in state.consensus}
    for sq in state.sub_questions:
        cs = consensus.get(sq.id)
        nodes.append(
            KGNode(
                id=f"hyp_{sq.id}",
                type="hypothesis",
                label=sq.hypothesis or sq.text,
                data={
                    "verdict": cs.verdict if cs else None,
                    "evidence_strength": cs.evidence_strength if cs else None,
                    "controversy_score": cs.controversy_score if cs else None,
                },
            )
        )

    stance_by_paper = {s.paper_id: s for s in state.paper_stances}
    paper_ids = {paper.paper_id for paper in state.papers}

    for paper in state.papers:
        stance = stance_by_paper.get(paper.paper_id)
        nodes.append(
            KGNode(
                id=paper.paper_id,
                type="paper",
                label=paper.title,
                data={
                    "year": paper.year,
                    "venue": paper.venue,
                    "citation_count": paper.citation_count,
                    "credibility_score": paper.credibility_score,
                    "final_score": paper.final_score,
                    "url": paper.url,
                    "stance": stance.label.value if stance else None,
                    "stance_confidence": stance.confidence if stance else None,
                },
            )
        )
        if stance and stance.label in _STANCE_EDGE:
            edges.append(
                KGEdge(
                    id=f"e_stance_{paper.paper_id}",
                    source=paper.paper_id,
                    target=f"hyp_{stance.sub_question_id}",
                    type=_STANCE_EDGE[stance.label],
                )
            )
        # Only surface citation edges between papers we actually retrieved —
        # a paper's full reference list is mostly papers outside our set, and
        # those wouldn't have nodes to point at.
        for ref_id in paper.references:
            if ref_id in paper_ids and ref_id != paper.paper_id:
                edges.append(
                    KGEdge(
                        id=f"e_cites_{paper.paper_id}_{ref_id}",
                        source=paper.paper_id,
                        target=ref_id,
                        type="cites",
                    )
                )

    for claim in state.claims:
        verdict = state.verdict_by_claim(claim.id)
        nodes.append(
            KGNode(
                id=claim.id,
                type="claim",
                label=claim.text,
                data={
                    "sub_question_id": claim.sub_question_id,
                    "stance": verdict.label.value if verdict else None,
                    "stance_confidence": verdict.confidence if verdict else None,
                    "fidelity": verdict.fidelity.value if verdict else None,
                },
            )
        )
        edges.append(
            KGEdge(
                id=f"e_extracted_{claim.id}",
                source=claim.id,
                target=claim.source_paper_id,
                type="extracted_from",
            )
        )

    state.knowledge_graph = KnowledgeGraph(nodes=nodes, edges=edges)
