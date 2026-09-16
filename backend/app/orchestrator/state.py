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
                AgentTrace(agent=self.name, status="completed", duration_ms=duration_ms)
            )
