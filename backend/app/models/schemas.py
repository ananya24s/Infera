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
    source: str = "semantic_scholar"  # semantic_scholar | arxiv

    # paper_ids (same scheme as Paper.paper_id, e.g. "s2:<id>") this paper cites,
    # as reported by the source API. Only populated for Semantic Scholar papers —
    # arXiv's Atom API doesn't expose a citation graph.
    references: list[str] = Field(default_factory=list)

    # populated by the ranking agent
    relevance_score: float = 0.0
    credibility_score: float = 0.0
    final_score: float = 0.0


class SubQuestion(BaseModel):
    id: str
    text: str
    rationale: str = ""


class Claim(BaseModel):
    id: str
    text: str
    sub_question_id: Optional[str] = None
    source_paper_id: str
    source_sentence: str = ""


class Verdict(BaseModel):
    claim_id: str
    label: VerificationLabel
    confidence: float
    evidence_sentence: str = ""


class StanceCluster(BaseModel):
    id: str
    topic: str
    claim_ids: list[str]
    dominant_label: VerificationLabel
    agreement_ratio: float  # fraction of claims agreeing with dominant_label


class ConsensusScore(BaseModel):
    sub_question_id: str
    evidence_strength: float  # 0 (no evidence / pure NEI) to 1 (strong, unanimous support)
    controversy_score: float  # 0 (unanimous) to 1 (maximally split)
    supports: int
    refutes: int
    not_enough_info: int


class KGNode(BaseModel):
    id: str
    type: str  # "paper" | "claim"
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


class ResearchResponse(BaseModel):
    question: str
    sub_questions: list[SubQuestion]
    papers: list[Paper]
    claims: list[Claim]
    verdicts: list[Verdict]
    clusters: list[StanceCluster]
    consensus: list[ConsensusScore]
    knowledge_graph: KnowledgeGraph
    report: ResearchReport
    trace: list[AgentTrace]
