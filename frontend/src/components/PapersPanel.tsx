import type { Paper } from "../types/api";

export default function PapersPanel({ papers }: { papers: Paper[] }) {
  return (
    <div className="panel papers-panel">
      <h2>Ranked Sources ({papers.length})</h2>
      <div className="papers-list">
        {papers.map((p) => (
          <div key={p.paper_id} className="paper-card">
            <a href={p.url ?? undefined} target="_blank" rel="noreferrer" className="paper-title">
              {p.title}
            </a>
            <div className="paper-meta">
              {p.year ?? "n.d."} · {p.venue ?? p.source} · {p.citation_count} citations
            </div>
            <div className="paper-scores">
              <span title="Relevance">rel {p.relevance_score.toFixed(2)}</span>
              <span title="Credibility">cred {p.credibility_score.toFixed(2)}</span>
              <span title="Final rank score" className="final">
                final {p.final_score.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
