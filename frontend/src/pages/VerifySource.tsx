import { useState } from "react";
import { verifySource } from "../lib/api";
import type { SingleSourceResult } from "../types/api";

const LABEL_CLASS: Record<string, string> = {
  SUPPORTS: "supports",
  REFUTES: "refutes",
  NOT_ENOUGH_INFO: "nei",
};

type Status = "idle" | "running" | "done" | "error";

export default function VerifySource() {
  const [hypothesis, setHypothesis] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<SingleSourceResult | null>(null);
  const [error, setError] = useState("");

  const canSubmit = hypothesis.trim() && sourceText.trim() && status !== "running";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setStatus("running");
    setError("");
    try {
      const isQuestion = hypothesis.trim().endsWith("?");
      const r = await verifySource({
        source_text: sourceText.trim(),
        ...(isQuestion ? { question: hypothesis.trim() } : { hypothesis: hypothesis.trim() }),
      });
      setResult(r);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setStatus("error");
    }
  }

  return (
    <div className="page">
      <p className="eyebrow">// single-source check</p>
      <h1 className="page-title">Does this source back that up?</h1>
      <p className="page-lead">
        Paste one source and a hypothesis (or a plain question) — no retrieval, no report, just the same NLI
        stance check the pipeline runs per-paper, on this one source.
      </p>

      <form className="verify-form" onSubmit={handleSubmit}>
        <label className="verify-label" htmlFor="verify-hypothesis">
          hypothesis or question
        </label>
        <input
          id="verify-hypothesis"
          type="text"
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          placeholder="Creatine improves memory in healthy adults."
          disabled={status === "running"}
        />

        <label className="verify-label" htmlFor="verify-source">
          source text (e.g. an abstract)
        </label>
        <textarea
          id="verify-source"
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          placeholder="Paste the abstract or passage to check…"
          rows={8}
          disabled={status === "running"}
        />

        <button type="submit" disabled={!canSubmit}>
          {status === "running" ? "checking…" : "check ↵"}
        </button>
      </form>

      {status === "error" && <div className="error-banner">{error}</div>}

      {status === "done" && result && (
        <div className="panel verify-result">
          <h2>result</h2>
          <div className="verify-result-top">
            <span className={`badge ${LABEL_CLASS[result.label]}`}>
              {result.label.replace(/_/g, " ")} ({Math.round(result.confidence * 100)}%)
            </span>
          </div>
          <div className="verify-result-hypothesis">
            hypothesis: <span>{result.hypothesis}</span>
          </div>
          {result.evidence_sentence ? (
            <p className="paper-evidence">“{result.evidence_sentence}”</p>
          ) : (
            <p className="empty">Nothing in the source text takes a clear position on this hypothesis.</p>
          )}
        </div>
      )}
    </div>
  );
}
