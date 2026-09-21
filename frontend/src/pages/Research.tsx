import { useEffect, useState } from "react";
import AgentTable from "../components/AgentTable";
import ClaimsPanel from "../components/ClaimsPanel";
import ConsensusPanel from "../components/ConsensusPanel";
import KnowledgeGraphView from "../components/KnowledgeGraphView";
import PapersPanel from "../components/PapersPanel";
import QueryForm from "../components/QueryForm";
import ReportView from "../components/ReportView";
import { useResearch } from "../context/ResearchContext";
import { EXAMPLE_QUESTIONS } from "../lib/examples";

type Tab = "report" | "graph" | "sources" | "claims";
const TABS: Tab[] = ["report", "graph", "sources", "claims"];

function useElapsedSeconds(startedAt: number | null): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (startedAt == null) return;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [startedAt]);
  return startedAt == null ? 0 : Math.max(0, (now - startedAt) / 1000);
}

export default function Research() {
  const { question, status, trace, result, error, startedAt, run } = useResearch();
  const [value, setValue] = useState(question);
  const [tab, setTab] = useState<Tab>("report");
  const elapsed = useElapsedSeconds(status === "running" ? startedAt : null);

  const totalSeconds = trace.reduce((sum, t) => sum + (t.status === "completed" ? (t.duration_ms ?? 0) : 0), 0) / 1000;

  return (
    <div className="page">
      <QueryForm onSubmit={run} loading={status === "running"} value={value} onChange={setValue} />

      {status === "idle" && (
        <div className="research-empty">
          <div className="term-block-title">$ history --sample</div>
          <div className="term-history">
            {EXAMPLE_QUESTIONS.map((q, i) => (
              <button
                key={q}
                className="term-history-item"
                onClick={() => {
                  setValue(q);
                  run(q);
                }}
              >
                <span className="history-index">{482 + i}</span>
                <span className="history-text">{q}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {status === "running" && (
        <div className="panel panel-loading">
          <h2>
            <span className="spinner" /> running pipeline · {elapsed.toFixed(0)}s
          </h2>
          <AgentTable trace={trace} live />
        </div>
      )}

      {status === "error" && (
        <>
          <div className="error-banner">{error}</div>
          {trace.length > 0 && <AgentTable trace={trace} live />}
        </>
      )}

      {status === "done" && result && (
        <>
          <div className="run-summary">
            <span className="run-question">{question}</span>
            <span className="run-stats">
              done in {totalSeconds.toFixed(1)}s · {result.papers.length} papers · {result.claims.length} claims ·{" "}
              {result.knowledge_graph.edges.length} graph edges
            </span>
          </div>

          <details className="trace-details">
            <summary>pipeline trace</summary>
            <AgentTable trace={trace} live />
          </details>

          <nav className="tabs">
            {TABS.map((t) => (
              <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </nav>

          {tab === "report" && (
            <>
              <ConsensusPanel consensus={result.consensus} subQuestions={result.sub_questions} />
              <ReportView report={result.report} />
            </>
          )}
          {tab === "graph" && <KnowledgeGraphView graph={result.knowledge_graph} />}
          {tab === "sources" && <PapersPanel papers={result.papers} />}
          {tab === "claims" && <ClaimsPanel claims={result.claims} verdicts={result.verdicts} />}
        </>
      )}
    </div>
  );
}
