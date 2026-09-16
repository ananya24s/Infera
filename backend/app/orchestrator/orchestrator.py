"""Hand-built sequential orchestrator.

Deliberately not a graph framework: the pipeline is a fixed, linear sequence
of agents that all share one ResearchState. Conditional/looping behavior
(Report Generation re-running Verification on its own draft) is expressed as
plain Python inside the agent function, not as orchestrator-level control
flow. This keeps the whole system inspectable in one file.
"""
from __future__ import annotations

from collections.abc import Callable

from app.orchestrator.state import AgentStep, ResearchState


class Orchestrator:
    def __init__(self) -> None:
        self._steps: list[AgentStep] = []

    def register(self, name: str, fn: Callable[[ResearchState], None]) -> "Orchestrator":
        self._steps.append(AgentStep(name, fn))
        return self

    def run(self, state: ResearchState) -> ResearchState:
        for step in self._steps:
            step.run(state)
        return state


def build_default_pipeline() -> Orchestrator:
    # Imported lazily so heavy ML deps only load when a pipeline is actually built.
    from app.agents.claim_extraction import run as claim_extraction
    from app.agents.consensus_scoring import run as consensus_scoring
    from app.agents.kg_builder import run as kg_builder
    from app.agents.query_planning import run as query_planning
    from app.agents.ranking import run as ranking
    from app.agents.report_generation import run as report_generation
    from app.agents.retrieval import run as retrieval
    from app.agents.stance_clustering import run as stance_clustering
    from app.agents.verification import run as verification

    orch = Orchestrator()
    orch.register("query_planning", query_planning)
    orch.register("retrieval", retrieval)
    orch.register("ranking", ranking)
    orch.register("claim_extraction", claim_extraction)
    orch.register("verification", verification)
    orch.register("stance_clustering", stance_clustering)
    orch.register("consensus_scoring", consensus_scoring)
    orch.register("kg_builder", kg_builder)
    orch.register("report_generation", report_generation)
    return orch
