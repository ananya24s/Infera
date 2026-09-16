import type { Claim, Verdict } from "../types/api";

const LABEL_CLASS: Record<string, string> = {
  SUPPORTS: "supports",
  REFUTES: "refutes",
  NOT_ENOUGH_INFO: "nei",
};

export default function ClaimsPanel({
  claims,
  verdicts,
}: {
  claims: Claim[];
  verdicts: Verdict[];
}) {
  const verdictByClaim = new Map(verdicts.map((v) => [v.claim_id, v]));

  return (
    <div className="panel claims-panel">
      <h2>Claims ({claims.length})</h2>
      <div className="claims-list">
        {claims.map((c) => {
          const v = verdictByClaim.get(c.id);
          return (
            <div key={c.id} className="claim-card">
              <div className="claim-text">{c.text}</div>
              {v && (
                <div className={`badge ${LABEL_CLASS[v.label]}`}>
                  {v.label} ({(v.confidence * 100).toFixed(0)}%)
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
