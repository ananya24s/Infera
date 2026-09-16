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
      <div className="term-chrome">
        <span className="term-dot term-dot-r" />
        <span className="term-dot term-dot-y" />
        <span className="term-dot term-dot-g" />
        <span className="term-chrome-title">guest@infera: ~/research</span>
      </div>

      <header className={`app-header ${showLanding ? "app-header-landing" : ""}`}>
        <div className="brand">
          <span className="brand-mark">infera<span className="brand-cursor" /></span>
          <span className="brand-badge">multi&#8209;agent research</span>
        </div>
        {showLanding && (
          <p className="tagline">
            Trained models decide relevance, verification, and consensus. The
            language model only phrases the report.
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

      {showLanding && (
        <div className="status-bar">
          <span>infera v0.1.0</span>
          <span>9 agents registered</span>
          <span>retrieval: semantic-scholar + arxiv</span>
          <span>verify: nli</span>
          <span>rank: lightgbm</span>
        </div>
      )}

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
