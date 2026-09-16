import type { ResearchRequest, ResearchResponse } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function runResearch(req: ResearchRequest): Promise<ResearchResponse> {
  const res = await fetch(`${API_BASE}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Request failed (${res.status}): ${detail}`);
  }
  return res.json();
}
