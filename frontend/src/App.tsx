import { useState } from "react";
import QueryForm from "./components/QueryForm";
import PipelineTrace from "./components/PipelineTrace";
import ConsensusPanel from "./components/ConsensusPanel";
import ReportView from "./components/ReportView";
import KnowledgeGraphView from "./components/KnowledgeGraphView";
import PapersPanel from "./components/PapersPanel";
import ClaimsPanel from "./components/ClaimsPanel";
import { runResearch } from "./lib/api";
import type { ResearchResponse } from "./types/api";
import "./App.css";

type Tab = "report" | "graph" | "sources" | "claims";

function App() {
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("report");

  const handleSubmit = async (question: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await runResearch({ question });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Infera</h1>
        <p className="tagline">
          Multi-agent research consensus engine — evidence-strength and controversy scores
          come from a trained NLI model and learned ranker, not LLM opinion.
        </p>
      </header>

      <QueryForm onSubmit={handleSubmit} loading={loading} />

      {error && <div className="error-banner">{error}</div>}

      {loading && (
        <div className="panel">
          <h2>Running pipeline…</h2>
          <PipelineTrace trace={result?.trace ?? []} />
        </div>
      )}

      {result && (
        <>
          <div className="panel">
            <PipelineTrace trace={result.trace} />
          </div>

          <nav className="tabs">
            {(["report", "graph", "sources", "claims"] as Tab[]).map((t) => (
              <button
                key={t}
                className={tab === t ? "active" : ""}
                onClick={() => setTab(t)}
              >
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

export default App;
