export type VerificationLabel = "SUPPORTS" | "REFUTES" | "NOT_ENOUGH_INFO";

export interface Paper {
  paper_id: string;
  title: string;
  abstract: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  citation_count: number;
  influential_citation_count: number;
  is_open_access: boolean;
  url: string | null;
  source: string;
  relevance_score: number;
  credibility_score: number;
  final_score: number;
  sub_question_id: string | null;
}

export interface SubQuestion {
  id: string;
  text: string;
  /** The sub-question as a declarative statement; sources are verified against this. */
  hypothesis: string;
  rationale: string;
}

export interface Claim {
  id: string;
  text: string;
  sub_question_id: string | null;
  source_paper_id: string;
  source_sentence: string;
}

/** A source's position on a hypothesis, judged from its most decisive abstract sentence. */
export interface PaperStance {
  paper_id: string;
  sub_question_id: string;
  label: VerificationLabel;
  confidence: number;
  evidence_sentence: string;
}

export interface Verdict {
  claim_id: string;
  /** Stance: does this finding support/refute the hypothesis? */
  label: VerificationLabel;
  confidence: number;
  /** Fidelity: does the claim's own source abstract actually support it? */
  fidelity: VerificationLabel;
  fidelity_confidence: number;
  evidence_sentence: string;
}

export interface StanceCluster {
  id: string;
  topic: string;
  claim_ids: string[];
  dominant_label: VerificationLabel;
  agreement_ratio: number;
}

export type ConsensusVerdict = "supported" | "refuted" | "mixed" | "insufficient";

export interface ConsensusScore {
  sub_question_id: string;
  evidence_strength: number;
  controversy_score: number;
  /** -1 (all decisive papers refute) to +1 (all support) */
  net_support: number;
  verdict: ConsensusVerdict;
  supports: number;
  refutes: number;
  not_enough_info: number;
}

export interface KGNode {
  id: string;
  type: "paper" | "claim" | "hypothesis";
  label: string;
  data: Record<string, unknown>;
}

export interface KGEdge {
  id: string;
  source: string;
  target: string;
  type: "supports" | "contradicts" | "cites" | "extracted_from";
}

export interface KnowledgeGraph {
  nodes: KGNode[];
  edges: KGEdge[];
}

export interface ResearchReport {
  question: string;
  summary: string;
  body_markdown: string;
  revised: boolean;
  revision_notes: string[];
  /** "template" (no LLM) or e.g. "ollama/qwen2.5:7b" */
  generated_by: string;
  /** cited sentences re-verified against the source they cite, and how many failed */
  checked_sentences: number;
  flagged_sentences: number;
}

export interface AgentTrace {
  agent: string;
  status: "started" | "completed" | "failed";
  detail: string;
  duration_ms: number | null;
}

export interface ResearchResponse {
  question: string;
  sub_questions: SubQuestion[];
  papers: Paper[];
  claims: Claim[];
  verdicts: Verdict[];
  paper_stances: PaperStance[];
  clusters: StanceCluster[];
  consensus: ConsensusScore[];
  knowledge_graph: KnowledgeGraph;
  report: ResearchReport;
  trace: AgentTrace[];
}

export interface ResearchRequest {
  question: string;
  max_papers?: number;
  max_sub_questions?: number;
}

export interface Health {
  status: string;
  llm: string;
}
