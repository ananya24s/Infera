"""Knowledge Graph Builder agent: paper + claim nodes, with
supports/contradicts/cites/extracted_from edges, derived entirely from
retrieval + verification output (no LLM-invented edges).
"""
from __future__ import annotations

from app.models.schemas import KGEdge, KGNode, KnowledgeGraph, VerificationLabel
from app.orchestrator.state import ResearchState


def run(state: ResearchState) -> None:
    nodes: list[KGNode] = []
    edges: list[KGEdge] = []

    paper_ids = {paper.paper_id for paper in state.papers}

    for paper in state.papers:
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
                },
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

    label_to_edge_type = {
        VerificationLabel.SUPPORTS: "supports",
        VerificationLabel.REFUTES: "contradicts",
    }

    for claim in state.claims:
        verdict = state.verdict_by_claim(claim.id)
        nodes.append(
            KGNode(
                id=claim.id,
                type="claim",
                label=claim.text,
                data={
                    "sub_question_id": claim.sub_question_id,
                    "label": verdict.label.value if verdict else None,
                    "confidence": verdict.confidence if verdict else None,
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
        if verdict and verdict.label in label_to_edge_type:
            edges.append(
                KGEdge(
                    id=f"e_verdict_{claim.id}",
                    source=claim.source_paper_id,
                    target=claim.id,
                    type=label_to_edge_type[verdict.label],
                )
            )

    state.knowledge_graph = KnowledgeGraph(nodes=nodes, edges=edges)
