import { useEffect, useState } from "react";
import { fetchHealth } from "../lib/api";
import type { Health } from "../types/api";

export default function StatusBar() {
  const [health, setHealth] = useState<Health | "offline" | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      fetchHealth()
        .then((h) => !cancelled && setHealth(h))
        .catch(() => !cancelled && setHealth("offline"));
    check();
    const id = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const offline = health === "offline";
  return (
    <div className="status-bar">
      <span>infera v0.1.0</span>
      <span className={offline ? "status-bad" : health ? "status-ok" : ""}>
        backend: {health === null ? "checking…" : offline ? "offline" : "online"}
      </span>
      {health && !offline && <span>llm: {health.llm}</span>}
      <span>retrieval: openalex + arxiv</span>
    </div>
  );
}
