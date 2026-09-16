import { useState } from "react";
import QueryForm from "./components/QueryForm";
import Hero from "./components/Hero";
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
  const [prefill, setPrefill] = useState("");

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

  const showLanding = !result && !loading;

  return (
    <div className="app">
      <div className="bg-glow" aria-hidden="true" />

      <header className={`app-header ${showLanding ? "app-header-landing" : ""}`}>
        <div className="brand">
          <span className="brand-mark">infera</span>
          <span className="brand-badge">multi-agent research</span>
        </div>
        {showLanding && (
          <p className="tagline">
            Ask a research question. Trained models — not LLM opinion — decide relevance,
            verification, and consensus. The LLM only phrases the report.
          </p>
        )}
      </header>

      <QueryForm
        onSubmit={handleSubmit}
        loading={loading}
        value={prefill}
        onChange={setPrefill}
      />

      {error && <div className="error-banner">{error}</div>}

      {showLanding && <Hero onExample={(q) => { setPrefill(q); handleSubmit(q); }} />}

      {loading && (
        <div className="panel panel-loading">
          <h2>
            <span className="spinner" /> Running pipeline…
          </h2>
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
