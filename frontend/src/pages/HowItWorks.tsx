import { useEffect, useState } from "react";
import { AGENTS } from "../lib/agents";
import { fetchHealth } from "../lib/api";

export default function HowItWorks() {
  const [llm, setLlm] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => setLlm(h.llm))
      .catch(() => setLlm(null));
  }, []);

  const models = [
    ["Verification (NLI)", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"],
    ["Embeddings", "sentence-transformers/all-MiniLM-L6-v2"],
    ["Ranking", "LightGBM (fixed-weight fallback until trained)"],
    ["Clustering", "HDBSCAN"],
    ["LLM (phrasing only)", llm ?? "backend offline"],
  ];

  return (
    <div className="page">
      <p className="eyebrow">// how infera works</p>
      <h1 className="page-title">Nine agents, one shared state.</h1>
      <p className="page-lead">
        A question moves through a fixed pipeline. Each stage reads and writes one shared state object, so
        the last stage can reach back and fact-check its own output with the same verification model.
      </p>

      <div className="principle">
        <span className="principle-tag">core principle</span>
        Ranking, verification and consensus scoring come from trained models. The LLM only phrases
        sentences and helps split text. It never decides what&apos;s true.
      </div>

      <div className="agent-list">
        {AGENTS.map((a, i) => (
          <div className="agent-card" key={a.name}>
            <div className="agent-card-head">
              <span className="agent-n">{String(i + 1).padStart(2, "0")}</span>
              <h3>{a.title}</h3>
              <span className={`col-kind kind-${a.kind}`}>{a.kind === "model" ? "trained model" : "llm phrasing"}</span>
            </div>
            <p className="agent-what">{a.what}</p>
            <p className="agent-how">{a.how}</p>
          </div>
        ))}
      </div>

      <div className="term-block-title">$ infera --models</div>
      <div className="term-table">
        {models.map(([k, v]) => (
          <div className="term-row models-row" key={k}>
            <span className="col-name">{k}</span>
            <span className="col-detail">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
