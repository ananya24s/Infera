"""Pydantic schemas shared across the API and the agent pipeline."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VerificationLabel(str, Enum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NOT_ENOUGH_INFO = "NOT_ENOUGH_INFO"


class Paper(BaseModel):
    paper_id: str
    title: str
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    citation_count: int = 0
    influential_citation_count: int = 0
    is_open_access: bool = False
    url: Optional[str] = None
    source: str = "openalex"  # openalex | arxiv

    # paper_ids (same scheme as Paper.paper_id, e.g. "openalex:<id>") this paper
    # cites, as reported by the source API. Only populated for OpenAlex papers —
    # arXiv's Atom API doesn't expose a citation graph.
    references: list[str] = Field(default_factory=list)

    # which sub-question retrieved this paper (set by the retrieval agent)
    sub_question_id: Optional[str] = None

    # populated by the ranking agent
    relevance_score: float = 0.0
    credibility_score: float = 0.0
    final_score: float = 0.0


class SubQuestion(BaseModel):
    id: str
    text: str
    # The sub-question as a declarative statement ("Creatine improves cognition."),
    # which is what sources are verified against — SciFact-style claim verification.
    hypothesis: str = ""
    rationale: str = ""


class Claim(BaseModel):
    id: str
    text: str
    sub_question_id: Optional[str] = None
    source_paper_id: str
    source_sentence: str = ""


class PaperStance(BaseModel):
    """A source's position on a sub-question's hypothesis, judged by the NLI
    model from the abstract sentence that speaks most directly to it."""

    paper_id: str
    sub_question_id: str
    label: VerificationLabel
    confidence: float
    evidence_sentence: str = ""


class SingleSourceRequest(BaseModel):
    """Check one pasted source against a hypothesis, outside the full research
    pipeline — no retrieval, no report, just the same NLI stance check the
    pipeline runs per-paper."""

    source_text: str
    hypothesis: str = ""
    # Used to derive `hypothesis` (rule-based, no LLM) when it's left blank.
    question: str = ""


class SingleSourceResult(BaseModel):
    hypothesis: str
    label: VerificationLabel
    confidence: float
    evidence_sentence: str = ""


class Verdict(BaseModel):
    """Two independent checks on an extracted claim."""

    claim_id: str
    # Stance: does this finding support/refute the sub-question's hypothesis?
    label: VerificationLabel
    confidence: float
    # Fidelity: does the claim's own source abstract actually support it?
    # (catches claims an LLM hallucinated or distorted during extraction)
    fidelity: VerificationLabel = VerificationLabel.NOT_ENOUGH_INFO
    fidelity_confidence: float = 0.0
    # The abstract sentence closest to the claim, for highlighting.
    evidence_sentence: str = ""


class StanceCluster(BaseModel):
    id: str
    topic: str
    claim_ids: list[str]
    dominant_label: VerificationLabel
    agreement_ratio: float  # fraction of claims agreeing with dominant_label


class ConsensusScore(BaseModel):
    """Aggregated over PAPER stances (each source counts once) for one sub-question."""

    sub_question_id: str
    evidence_strength: float  # 0-1: how much decisive, confident evidence exists
    controversy_score: float  # 0 (all decisive sources agree) to 1 (split evenly)
    net_support: float = 0.0  # -1 (all decisive sources refute) to +1 (all support)
    verdict: str = "insufficient"  # supported | refuted | mixed | insufficient
    supports: int  # number of papers
    refutes: int
    not_enough_info: int


class KGNode(BaseModel):
    id: str
    type: str  # "paper" | "claim" | "hypothesis"
    label: str
    data: dict = Field(default_factory=dict)


class KGEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # "supports" | "contradicts" | "cites" | "extracted_from"


class KnowledgeGraph(BaseModel):
    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)


class ResearchRequest(BaseModel):
    question: str
    max_papers: int = 25
    max_sub_questions: int = 5


class AgentTrace(BaseModel):
    agent: str
    status: str  # "started" | "completed" | "failed"
    detail: str = ""
    duration_ms: Optional[float] = None


class ResearchReport(BaseModel):
    question: str
    summary: str
    body_markdown: str
    revised: bool = False
    revision_notes: list[str] = Field(default_factory=list)
    # "template" (no LLM) or e.g. "ollama/qwen2.5:7b" (LLM-drafted and self-checked)
    generated_by: str = "template"
    # self-check: cited sentences re-verified against the source they cite
    checked_sentences: int = 0
    flagged_sentences: int = 0


class ResearchResponse(BaseModel):
    question: str
    sub_questions: list[SubQuestion]
    papers: list[Paper]
    claims: list[Claim]
    verdicts: list[Verdict]
    paper_stances: list[PaperStance]
    clusters: list[StanceCluster]
    consensus: list[ConsensusScore]
    knowledge_graph: KnowledgeGraph
    report: ResearchReport
    trace: list[AgentTrace]
