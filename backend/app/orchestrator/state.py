"""The shared mutable state object that flows through every agent.

This is the entire "orchestration" primitive: agents are plain callables that
read fields off a ResearchState and write new fields onto it. There is no
graph library, no node/edge DSL — just a dataclass and a list of steps run
in order by Orchestrator.run(). Keeping the state on one object (rather than
threading a chain of return values) makes it trivial for a later agent
(e.g. Report Generation) to reach back into anything an earlier agent produced
(e.g. re-running Verification against its own drafted sentences).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.models.schemas import (
    AgentTrace,
    Claim,
    ConsensusScore,
    KnowledgeGraph,
    Paper,
    PaperStance,
    ResearchReport,
    StanceCluster,
    SubQuestion,
    Verdict,
)


@dataclass
class ResearchState:
    question: str
    max_papers: int = 25
    max_sub_questions: int = 5

    sub_questions: list[SubQuestion] = field(default_factory=list)
    papers: list[Paper] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    verdicts: list[Verdict] = field(default_factory=list)
    paper_stances: list[PaperStance] = field(default_factory=list)
    clusters: list[StanceCluster] = field(default_factory=list)
    consensus: list[ConsensusScore] = field(default_factory=list)
    knowledge_graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    report: ResearchReport | None = None

    trace: list[AgentTrace] = field(default_factory=list)

    def paper_by_id(self, paper_id: str) -> Paper | None:
        return next((p for p in self.papers if p.paper_id == paper_id), None)

    def claim_by_id(self, claim_id: str) -> Claim | None:
        return next((c for c in self.claims if c.id == claim_id), None)

    def verdict_by_claim(self, claim_id: str) -> Verdict | None:
        return next((v for v in self.verdicts if v.claim_id == claim_id), None)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _verification_summary(s: "ResearchState") -> str:
    counts = {"SUPPORTS": 0, "REFUTES": 0, "NOT_ENOUGH_INFO": 0}
    for st in s.paper_stances:
        counts[st.label.value] += 1
    return f"{len(s.paper_stances)} papers: {counts['SUPPORTS']} support / {counts['REFUTES']} refute / {counts['NOT_ENOUGH_INFO']} neutral"


def _consensus_summary(s: "ResearchState") -> str:
    return ", ".join(f"{c.verdict} (controversy {c.controversy_score:.2f})" for c in s.consensus) or "no stances"


# Short human-readable result of each stage, shown in the live progress view.
_SUMMARIES = {
    "query_planning": lambda s: _plural(len(s.sub_questions), "sub-question"),
    "retrieval": lambda s: _plural(len(s.papers), "paper"),
    "ranking": lambda s: f"top score {s.papers[0].final_score:.2f}" if s.papers else "no papers",
    "claim_extraction": lambda s: _plural(len(s.claims), "claim"),
    "verification": _verification_summary,
    "stance_clustering": lambda s: _plural(len(s.clusters), "cluster"),
    "consensus_scoring": _consensus_summary,
    "kg_builder": lambda s: f"{len(s.knowledge_graph.nodes)} nodes, {len(s.knowledge_graph.edges)} edges",
    "report_generation": lambda s: (
        s.report.generated_by
        + (f", {s.report.checked_sentences} citations checked, {s.report.flagged_sentences} flagged" if s.report.checked_sentences else "")
        if s.report else ""
    ),
}


def _summarize(name: str, state: "ResearchState") -> str:
    try:
        return _SUMMARIES[name](state) if name in _SUMMARIES else ""
    except Exception:  # noqa: BLE001 - a cosmetic summary must never break the pipeline
        return ""


class AgentStep:
    """Wraps a single pipeline stage so the orchestrator can trace it uniformly."""

    def __init__(self, name: str, fn):
        self.name = name
        self.fn = fn

    def run(self, state: ResearchState) -> None:
        start = time.perf_counter()
        state.trace.append(AgentTrace(agent=self.name, status="started"))
        try:
            self.fn(state)
        except Exception as exc:  # noqa: BLE001 - surfaced in trace, re-raised for the API layer
            state.trace.append(
                AgentTrace(agent=self.name, status="failed", detail=str(exc))
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            state.trace.append(
                AgentTrace(
                    agent=self.name,
                    status="completed",
                    detail=_summarize(self.name, state),
                    duration_ms=duration_ms,
                )
            )
