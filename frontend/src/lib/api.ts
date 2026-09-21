import type { AgentTrace, Health, ResearchRequest, ResearchResponse } from "../types/api";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8001";

export interface StreamHandlers {
  onTrace: (t: AgentTrace) => void;
  onResult: (r: ResearchResponse) => void;
  onError: (message: string) => void;
}

async function describeHttpError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // not JSON — fall through
  }
  return `Request failed (${res.status})`;
}

function dispatchEvent(block: string, h: StreamHandlers) {
  let event = "message";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7);
    else if (line.startsWith("data: ")) data += line.slice(6);
  }
  if (!data) return;
  const payload = JSON.parse(data);
  if (event === "trace") h.onTrace(payload);
  else if (event === "result") h.onResult(payload);
  else if (event === "error") h.onError(payload.detail ?? "Pipeline failed");
}

/** POSTs a question and streams pipeline progress (server-sent events over fetch,
 *  since EventSource can't POST). Resolves when the stream ends. */
export async function streamResearch(
  req: ResearchRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/research/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal,
    });
  } catch {
    if (signal?.aborted) return;
    throw new Error(
      `Can't reach the backend at ${API_BASE}. Is it running? (uvicorn app.main:app --port 8001)`,
    );
  }
  if (!res.ok || !res.body) throw new Error(await describeHttpError(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      dispatchEvent(buffer.slice(0, end), handlers);
      buffer = buffer.slice(end + 2);
    }
  }
}

export async function fetchHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json();
}
