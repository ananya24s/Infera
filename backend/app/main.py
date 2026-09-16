from __future__ import annotations

import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import ResearchRequest, ResearchResponse
from app.orchestrator.orchestrator import build_default_pipeline
from app.orchestrator.state import ResearchState

app = FastAPI(title="Infera", description="Multi-agent research consensus platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_default_pipeline()
    return _pipeline


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/research", response_model=ResearchResponse)
async def research(req: ResearchRequest) -> ResearchResponse:
    state = ResearchState(
        question=req.question,
        max_papers=req.max_papers,
        max_sub_questions=req.max_sub_questions,
    )
    pipeline = get_pipeline()

    try:
        # Runs the fully synchronous agent pipeline off the event loop thread,
        # since individual agents use asyncio.run() internally for their own
        # async calls (LLM, retrieval APIs).
        await asyncio.to_thread(pipeline.run, state)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if state.report is None:
        raise HTTPException(status_code=500, detail="Pipeline finished without producing a report")

    return ResearchResponse(
        question=state.question,
        sub_questions=state.sub_questions,
        papers=state.papers,
        claims=state.claims,
        verdicts=state.verdicts,
        clusters=state.clusters,
        consensus=state.consensus,
        knowledge_graph=state.knowledge_graph,
        report=state.report,
        trace=state.trace,
    )
