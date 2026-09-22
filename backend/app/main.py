from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.schemas import ResearchRequest, ResearchResponse
from app.orchestrator.orchestrator import build_default_pipeline
from app.orchestrator.state import ResearchState
from app.rate_limit import enforce_rate_limit

logger = logging.getLogger(__name__)

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_default_pipeline()
    return _pipeline


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load the NLI checkpoint and embedding model now, not on the first
    request — otherwise the first real user pays for the (multi-minute, on
    a cold cache) HuggingFace download and model load."""
    from app.ml import nli_model
    from app.services import hybrid_search

    logger.info("Warming up models...")
    get_pipeline()
    await asyncio.to_thread(nli_model.warmup)
    await asyncio.to_thread(hybrid_search.warmup)
    logger.info("Model warmup complete.")
    yield


app = FastAPI(
    title="Infera",
    description="Multi-agent research consensus platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict:
    from app.services.llm_client import llm_description

    return {"status": "ok", "llm": llm_description()}


def _build_response(state: ResearchState) -> ResearchResponse:
    if state.report is None:
        raise HTTPException(status_code=500, detail="Pipeline finished without producing a report")
    return ResearchResponse(
        question=state.question,
        sub_questions=state.sub_questions,
        papers=state.papers,
        claims=state.claims,
        verdicts=state.verdicts,
        paper_stances=state.paper_stances,
        clusters=state.clusters,
        consensus=state.consensus,
        knowledge_graph=state.knowledge_graph,
        report=state.report,
        trace=state.trace,
    )


def _new_state(req: ResearchRequest) -> ResearchState:
    return ResearchState(
        question=req.question,
        max_papers=req.max_papers,
        max_sub_questions=req.max_sub_questions,
    )


@app.post(
    "/api/research",
    response_model=ResearchResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def research(req: ResearchRequest) -> ResearchResponse:
    state = _new_state(req)
    try:
        # Runs the fully synchronous agent pipeline off the event loop thread,
        # since individual agents use asyncio.run() internally for their own
        # async calls (LLM, retrieval APIs).
        await asyncio.to_thread(get_pipeline().run, state)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _build_response(state)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/research/stream", dependencies=[Depends(enforce_rate_limit)])
async def research_stream(req: ResearchRequest) -> StreamingResponse:
    """Same pipeline as /api/research, but streams a `trace` event as each agent
    starts/finishes, then a final `result` (or `error`) event, so the UI can show
    live progress instead of one long silent wait."""
    state = _new_state(req)
    pipeline = get_pipeline()

    async def events():
        task = asyncio.create_task(asyncio.to_thread(pipeline.run, state))
        sent = 0
        while True:
            # The worker thread appends to state.trace; we just tail it.
            while sent < len(state.trace):
                yield _sse("trace", state.trace[sent].model_dump(mode="json"))
                sent += 1
            if task.done():
                break
            await asyncio.sleep(0.15)

        if task.exception() is not None:
            yield _sse("error", {"detail": str(task.exception())})
            return
        try:
            yield _sse("result", _build_response(state).model_dump(mode="json"))
        except HTTPException as exc:
            yield _sse("error", {"detail": exc.detail})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
