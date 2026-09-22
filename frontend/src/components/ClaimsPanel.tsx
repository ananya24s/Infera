import type { Claim, Verdict } from "../types/api";

const LABEL_CLASS: Record<string, string> = {
  SUPPORTS: "supports",
  REFUTES: "refutes",
  NOT_ENOUGH_INFO: "nei",
};

export default function ClaimsPanel({ claims, verdicts }: { claims: Claim[]; verdicts: Verdict[] }) {
  const verdictByClaim = new Map(verdicts.map((v) => [v.claim_id, v]));

  return (
    <div className="panel claims-panel">
      <h2>Claims ({claims.length})</h2>
      <p className="panel-note">
        Each claim gets two independent checks: its <b>stance</b> on the hypothesis, and its <b>source
        check</b> (does its own abstract actually back it up).
      </p>
      <div className="claims-list">
        {claims.map((c) => {
          const v = verdictByClaim.get(c.id);
          return (
            <div key={c.id} className="claim-card">
              <div className="claim-text">{c.text}</div>
              {v && (
                <div className="claim-badges">
                  <span className={`badge ${LABEL_CLASS[v.label]}`} title="Stance toward the hypothesis">
                    stance: {v.label.replace(/_/g, " ").toLowerCase()} ({Math.round(v.confidence * 100)}%)
                  </span>
                  <span className={`badge ${LABEL_CLASS[v.fidelity]}`} title="Is the claim supported by its own source abstract?">
                    source check: {v.fidelity === "SUPPORTS" ? "verified" : v.fidelity === "REFUTES" ? "contradicted" : "unverified"}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
