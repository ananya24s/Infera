import { AGENTS } from "../lib/agents";
import type { AgentTrace } from "../types/api";

type RowState = "idle" | "queued" | "running" | "done" | "failed";

function formatDuration(ms: number | null): string {
  if (ms == null) return "";
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function rowFor(name: string, trace: AgentTrace[], live: boolean) {
  const last = [...trace].reverse().find((t) => t.agent === name);
  let state: RowState = live ? "queued" : "idle";
  if (last?.status === "started") state = "running";
  else if (last?.status === "completed") state = "done";
  else if (last?.status === "failed") state = "failed";
  return { state, detail: last?.detail ?? "", time: formatDuration(last?.duration_ms ?? null) };
}

interface Props {
  trace: AgentTrace[];
  /** live = show progress columns (detail + time); otherwise a static idle listing. */
  live?: boolean;
}

export default function AgentTable({ trace, live = false }: Props) {
  return (
    <div className={`term-table ${live ? "term-table-live" : ""}`}>
      <div className="term-row term-row-head">
        <span className="col-pid">PID</span>
        <span className="col-name">AGENT</span>
        <span className="col-kind">SOURCE</span>
        <span className="col-state">STATE</span>
        {live && <span className="col-detail">RESULT</span>}
        {live && <span className="col-time">TIME</span>}
      </div>
      {AGENTS.map((agent, i) => {
        const row = rowFor(agent.name, trace, live);
        return (
          <div className={`term-row row-${row.state}`} key={agent.name}>
            <span className="col-pid">{String(i + 1).padStart(2, "0")}</span>
            <span className="col-name">{agent.name}</span>
            <span className={`col-kind kind-${agent.kind}`}>{agent.kind}</span>
            <span className="col-state">
              <i className="state-dot" />
              {row.state}
            </span>
            {live && <span className="col-detail">{row.detail}</span>}
            {live && <span className="col-time">{row.time}</span>}
          </div>
        );
      })}
    </div>
  );
}
