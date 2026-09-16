import type { AgentTrace } from "../types/api";

const AGENT_LABELS: Record<string, string> = {
  query_planning: "Query Planning",
  retrieval: "Retrieval",
  ranking: "Ranking",
  claim_extraction: "Claim Extraction",
  verification: "Verification",
  stance_clustering: "Stance Clustering",
  consensus_scoring: "Consensus/Controversy Scoring",
  kg_builder: "Knowledge Graph Builder",
  report_generation: "Report Generation",
};

export default function PipelineTrace({ trace }: { trace: AgentTrace[] }) {
  const completed = new Map<string, AgentTrace>();
  for (const t of trace) {
    if (t.status !== "started") completed.set(t.agent, t);
  }

  return (
    <div className="pipeline-trace">
      {Object.keys(AGENT_LABELS).map((agent) => {
        const t = completed.get(agent);
        const status = t?.status ?? (trace.some((x) => x.agent === agent) ? "running" : "pending");
        return (
          <div key={agent} className={`trace-step trace-${status}`}>
            <span className="trace-dot" />
            <span className="trace-name">{AGENT_LABELS[agent]}</span>
            {t?.duration_ms != null && (
              <span className="trace-duration">{Math.round(t.duration_ms)}ms</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
