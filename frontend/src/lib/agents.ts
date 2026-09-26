export interface AgentInfo {
  name: string;
  kind: "llm" | "model";
  title: string;
  what: string;
  how: string;
}

/** Pipeline order. `kind` is who makes the judgment: a trained model, or an
 *  LLM used only for phrasing/segmentation help. */
export const AGENTS: AgentInfo[] = [
  {
    name: "query_planning",
    kind: "llm",
    title: "Query Planning",
    what: "Splits your question into focused, searchable sub-questions.",
    how: "LLM phrasing help. Falls back to rule-based splitting when no LLM is available.",
  },
  {
    name: "retrieval",
    kind: "model",
    title: "Retrieval",
    what: "Finds real papers on OpenAlex and arXiv, then keeps the best matches.",
    how: "Dense embeddings (sentence-transformers + FAISS) blended with BM25 keyword scores.",
  },
  {
    name: "ranking",
    kind: "model",
    title: "Ranking",
    what: "Scores each paper for relevance and credibility.",
    how: "LightGBM ranker over hybrid-search score, citations, recency and open access. Uses transparent fixed weights until a trained ranker is loaded.",
  },
  {
    name: "claim_extraction",
    kind: "llm",
    title: "Claim Extraction",
    what: "Pulls atomic, checkable claims out of the top abstracts.",
    how: "LLM segmentation help. Falls back to plain sentence splitting.",
  },
  {
    name: "verification",
    kind: "model",
    title: "Verification",
    what: "Labels each claim SUPPORTS, REFUTES or NOT ENOUGH INFO against its source.",
    how: "NLI model (DeBERTa-v3), fine-tuned on real SciFact data with a class-weighted loss.",
  },
  {
    name: "stance_clustering",
    kind: "model",
    title: "Stance Clustering",
    what: "Groups related claims to show where sources agree or disagree.",
    how: "HDBSCAN over claim embeddings, split by verdict.",
  },
  {
    name: "consensus_scoring",
    kind: "model",
    title: "Consensus Scoring",
    what: "Turns verdicts into an evidence-strength score and a controversy score.",
    how: "Plain arithmetic over model outputs. No LLM opinion involved.",
  },
  {
    name: "kg_builder",
    kind: "model",
    title: "Knowledge Graph",
    what: "Builds a graph of papers and claims and how they relate.",
    how: "Nodes: papers, claims. Edges: supports, contradicts, cites, extracted-from.",
  },
  {
    name: "report_generation",
    kind: "llm",
    title: "Report Generation",
    what: "Drafts the report, then fact-checks its own sentences and revises unsupported ones.",
    how: "LLM drafting, with the same NLI model acting as the checker.",
  },
];
