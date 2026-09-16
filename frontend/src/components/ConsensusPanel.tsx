import type { ConsensusScore, SubQuestion } from "../types/api";

export default function ConsensusPanel({
  consensus,
  subQuestions,
}: {
  consensus: ConsensusScore[];
  subQuestions: SubQuestion[];
}) {
  const topicFor = (id: string) => subQuestions.find((s) => s.id === id)?.text ?? id;

  return (
    <div className="panel consensus-panel">
      <h2>Consensus & Controversy</h2>
      {consensus.length === 0 && <p className="empty">No consensus data yet.</p>}
      {consensus.map((c) => (
        <div key={c.sub_question_id} className="consensus-card">
          <div className="consensus-topic">{topicFor(c.sub_question_id)}</div>
          <div className="consensus-bars">
            <div className="bar-row">
              <span>Evidence strength</span>
              <div className="bar-track">
                <div
                  className="bar-fill strength"
                  style={{ width: `${c.evidence_strength * 100}%` }}
                />
              </div>
              <span>{c.evidence_strength.toFixed(2)}</span>
            </div>
            <div className="bar-row">
              <span>Controversy</span>
              <div className="bar-track">
                <div
                  className="bar-fill controversy"
                  style={{ width: `${c.controversy_score * 100}%` }}
                />
              </div>
              <span>{c.controversy_score.toFixed(2)}</span>
            </div>
          </div>
          <div className="consensus-counts">
            <span className="badge supports">SUPPORTS {c.supports}</span>
            <span className="badge refutes">REFUTES {c.refutes}</span>
            <span className="badge nei">NEI {c.not_enough_info}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
