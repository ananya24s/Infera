import json

from fastapi.testclient import TestClient

import app.main as main
from app.models.schemas import AgentTrace, ResearchReport
from app.orchestrator.state import AgentStep, ResearchState


class _FakePipeline:
    """Runs two real AgentSteps (so traces + summaries are the real thing)
    without loading any ML model."""

    def __init__(self, fail: bool = False):
        self.fail = fail

    def run(self, state: ResearchState) -> None:
        AgentStep("query_planning", lambda s: None).run(state)
        if self.fail:
            def boom(_s):
                raise RuntimeError("retrieval blew up")

            AgentStep("retrieval", boom).run(state)
        state.report = ResearchReport(question=state.question, summary="s", body_markdown="## Summary\nok")


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_stream_emits_trace_events_then_result(monkeypatch):
    monkeypatch.setattr(main, "get_pipeline", lambda: _FakePipeline())
    client = TestClient(main.app)

    resp = client.post("/api/research/stream", json={"question": "does x cause y?"})
    assert resp.status_code == 200
    events = _parse_sse(resp.text)

    kinds = [k for k, _ in events]
    assert kinds[-1] == "result"
    assert kinds.count("trace") == 2  # started + completed for the one step
    trace_payloads = [d for k, d in events if k == "trace"]
    assert [t["status"] for t in trace_payloads] == ["started", "completed"]
    assert events[-1][1]["report"]["body_markdown"].startswith("## Summary")


def test_stream_reports_pipeline_failure_as_error_event(monkeypatch):
    monkeypatch.setattr(main, "get_pipeline", lambda: _FakePipeline(fail=True))
    client = TestClient(main.app)

    resp = client.post("/api/research/stream", json={"question": "does x cause y?"})
    events = _parse_sse(resp.text)

    assert events[-1][0] == "error"
    assert "retrieval blew up" in events[-1][1]["detail"]
    failed = [d for k, d in events if k == "trace" and d["status"] == "failed"]
    assert failed and failed[0]["agent"] == "retrieval"


def test_agent_step_records_summary_detail():
    state = ResearchState(question="q")
    AgentStep("retrieval", lambda s: None).run(state)
    completed = [t for t in state.trace if isinstance(t, AgentTrace) and t.status == "completed"][0]
    assert completed.detail == "0 papers"
