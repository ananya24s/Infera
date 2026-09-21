import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { streamResearch } from "../lib/api";
import type { AgentTrace, ResearchResponse } from "../types/api";

export type RunStatus = "idle" | "running" | "done" | "error";

interface ResearchContextValue {
  question: string;
  status: RunStatus;
  /** Live trace while running; the result's own trace once done. */
  trace: AgentTrace[];
  result: ResearchResponse | null;
  error: string | null;
  startedAt: number | null;
  run: (question: string) => void;
}

const STORAGE_KEY = "infera:last-run";

const ResearchContext = createContext<ResearchContextValue | null>(null);

function loadSaved(): { question: string; result: ResearchResponse } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function save(question: string, result: ResearchResponse) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ question, result }));
  } catch {
    // storage full or unavailable — the run still works, it just won't survive a refresh
  }
}

export function ResearchProvider({ children }: { children: ReactNode }) {
  const saved = useRef(loadSaved()).current;
  const [question, setQuestion] = useState(saved?.question ?? "");
  const [status, setStatus] = useState<RunStatus>(saved ? "done" : "idle");
  const [trace, setTrace] = useState<AgentTrace[]>(saved?.result.trace ?? []);
  const [result, setResult] = useState<ResearchResponse | null>(saved?.result ?? null);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const run = useCallback((q: string) => {
    const text = q.trim();
    if (!text) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setQuestion(text);
    setStatus("running");
    setError(null);
    setResult(null);
    setTrace([]);
    setStartedAt(Date.now());

    streamResearch(
      { question: text },
      {
        onTrace: (t) => setTrace((prev) => [...prev, t]),
        onResult: (r) => {
          setResult(r);
          setTrace(r.trace);
          setStatus("done");
          save(text, r);
        },
        onError: (message) => {
          setError(message);
          setStatus("error");
        },
      },
      controller.signal,
    ).catch((err: unknown) => {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    });
  }, []);

  return (
    <ResearchContext.Provider value={{ question, status, trace, result, error, startedAt, run }}>
      {children}
    </ResearchContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useResearch(): ResearchContextValue {
  const ctx = useContext(ResearchContext);
  if (!ctx) throw new Error("useResearch must be used inside <ResearchProvider>");
  return ctx;
}
