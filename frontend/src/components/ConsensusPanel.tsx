import type { ConsensusScore, SubQuestion } from "../types/api";

const VERDICT_CLASS: Record<string, string> = {
  supported: "supports",
  refuted: "refutes",
  mixed: "controversial",
  insufficient: "nei",
};

export default function ConsensusPanel({
  consensus,
  subQuestions,
}: {
  consensus: ConsensusScore[];
  subQuestions: SubQuestion[];
}) {
  const sqFor = (id: string) => subQuestions.find((s) => s.id === id);

  return (
    <div className="panel consensus-panel">
      <h2>Consensus &amp; controversy</h2>
      {consensus.length === 0 && <p className="empty">No source took a position on this question.</p>}
      {consensus.map((c) => {
        const sq = sqFor(c.sub_question_id);
        const total = c.supports + c.refutes + c.not_enough_info;
        return (
          <div key={c.sub_question_id} className="consensus-card">
            <div className="consensus-topic">{sq?.hypothesis || sq?.text || c.sub_question_id}</div>
            <div className="consensus-verdict">
              <span className={`badge ${VERDICT_CLASS[c.verdict]}`}>{c.verdict}</span>
              <span className="consensus-verdict-note">
                {c.supports} of {total} papers support it · {c.refutes} refute · {c.not_enough_info} take no clear position
              </span>
            </div>
            <div className="consensus-bars">
              <div className="bar-row" title="How much decisive, confident evidence exists: share of papers taking a position × model confidence × sample size">
                <span>Evidence strength</span>
                <div className="bar-track">
                  <div className="bar-fill strength" style={{ width: `${c.evidence_strength * 100}%` }} />
                </div>
                <span>{c.evidence_strength.toFixed(2)}</span>
              </div>
              <div className="bar-row" title="How split the decisive papers are: 0 = they all agree, 1 = split evenly between support and refute">
                <span>Controversy</span>
                <div className="bar-track">
                  <div className="bar-fill controversy" style={{ width: `${c.controversy_score * 100}%` }} />
                </div>
                <span>{c.controversy_score.toFixed(2)}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
