import sample from "../data/sample.json";

const LABEL_CLASS: Record<string, string> = {
  SUPPORTS: "supports",
  REFUTES: "refutes",
  NOT_ENOUGH_INFO: "nei",
};

export default function SamplePreview() {
  const { _meta: meta, question, consensus, claims, sources } = sample;
  return (
    <div className="sample-card">
      <div className="sample-meta">
        real output · captured {meta.captured} · {meta.papers_retrieved} papers retrieved ·{" "}
        {meta.claims_checked} claims checked
      </div>

      <div className="sample-question">
        <span className="prompt-prefix">research@infera:~$</span> {question}
      </div>

      <div className="sample-grid">
        <div className="sample-col">
          <div className="sample-label"># consensus</div>
          <div className="bar-row">
            <span>Evidence strength</span>
            <div className="bar-track">
              <div className="bar-fill strength" style={{ width: `${consensus.evidence_strength * 100}%` }} />
            </div>
            <span>{consensus.evidence_strength.toFixed(2)}</span>
          </div>
          <div className="bar-row">
            <span>Controversy</span>
            <div className="bar-track">
              <div className="bar-fill controversy" style={{ width: `${consensus.controversy_score * 100}%` }} />
            </div>
            <span>{consensus.controversy_score.toFixed(2)}</span>
          </div>
          <div className="consensus-counts">
            <span className="badge supports">SUPPORTS {consensus.supports}</span>
            <span className="badge refutes">REFUTES {consensus.refutes}</span>
            <span className="badge nei">NEI {consensus.not_enough_info}</span>
          </div>

          <div className="sample-label sample-label-gap"># top sources</div>
          <ul className="sample-sources">
            {sources.map((s) => (
              <li key={s.title}>
                <a href={s.url ?? undefined} target="_blank" rel="noreferrer">{s.title}</a>
                <span>{s.year} · {s.citations} citations · score {s.score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="sample-col">
          <div className="sample-label"># claims, each checked against its source</div>
          {claims.map((c) => (
            <div className="sample-claim" key={c.text}>
              <div className={`badge ${LABEL_CLASS[c.label]}`}>
                {c.label.replace(/_/g, " ")} ({Math.round(c.confidence * 100)}%)
              </div>
              <div className="sample-claim-text">{c.text}</div>
              <div className="sample-claim-src">
                {c.source_title} ({c.source_year})
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
