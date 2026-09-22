import type { Paper, PaperStance } from "../types/api";

const LABEL_CLASS: Record<string, string> = {
  SUPPORTS: "supports",
  REFUTES: "refutes",
  NOT_ENOUGH_INFO: "nei",
};

export default function PapersPanel({ papers, stances }: { papers: Paper[]; stances: PaperStance[] }) {
  const stanceFor = new Map(stances.map((s) => [s.paper_id, s]));

  return (
    <div className="panel papers-panel">
      <h2>Ranked sources ({papers.length})</h2>
      <div className="papers-list">
        {papers.map((p) => {
          const st = stanceFor.get(p.paper_id);
          return (
            <div key={p.paper_id} className="paper-card">
              <a href={p.url ?? undefined} target="_blank" rel="noreferrer" className="paper-title">
                {p.title}
              </a>
              <div className="paper-meta">
                {p.year ?? "n.d."} · {p.venue ?? p.source} · {p.citation_count} citations
              </div>
              {st && (
                <div className="paper-stance">
                  <span className={`badge ${LABEL_CLASS[st.label]}`}>
                    {st.label.replace(/_/g, " ")} ({Math.round(st.confidence * 100)}%)
                  </span>
                  {st.evidence_sentence && <span className="paper-evidence">“{st.evidence_sentence}”</span>}
                </div>
              )}
              <div className="paper-scores">
                <span title="Relevance">rel {p.relevance_score.toFixed(2)}</span>
                <span title="Credibility">cred {p.credibility_score.toFixed(2)}</span>
                <span title="Final rank score" className="final">
                  final {p.final_score.toFixed(2)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
