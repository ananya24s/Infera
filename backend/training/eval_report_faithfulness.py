"""Evaluate Report Faithfulness: the share of cited report sentences that pass
re-verification against the exact source they cite, before any revision pass
fixes them (slide 8's "Report Faithfulness" metric).

The self-check already runs live in report_generation._generate() for every
request — it populates ResearchReport.checked_sentences and .flagged_sentences
(see app/agents/report_generation.py:278-284). This script just runs the full
pipeline end-to-end for a batch of real questions and aggregates those two
numbers into a tracked metric, instead of it only existing per-request.

Needs a running Ollama (report drafting is skipped, and nothing gets checked,
without an LLM — see app/agents/report_generation.py:run). Hits real
OpenAlex/arXiv via retrieval, so each question takes real wall-clock time
(network + generation), not GPU/CPU training time.

Usage:
    python -m training.eval_report_faithfulness
    python -m training.eval_report_faithfulness --questions_file questions.txt --json_out out.json
"""
from __future__ import annotations

import argparse
import json
import logging

DEFAULT_QUESTIONS = [
    "Does creatine improve cognitive performance in healthy adults?",
    "Is intermittent fasting effective for long-term weight loss?",
    "Does meditation reduce symptoms of anxiety?",
    "Can vitamin D supplementation prevent respiratory infections?",
    "Does caffeine consumption improve endurance exercise performance?",
]


def _run_one(question: str, max_papers: int = 25) -> dict:
    from app.orchestrator.orchestrator import build_default_pipeline
    from app.orchestrator.state import ResearchState

    state = ResearchState(question=question, max_papers=max_papers)
    build_default_pipeline().run(state)

    report = state.report
    if report is None:
        return {"question": question, "generated_by": "none", "checked": 0, "flagged": 0}
    return {
        "question": question,
        "generated_by": report.generated_by,
        "checked": report.checked_sentences,
        "flagged": report.flagged_sentences,
    }


def evaluate(questions: list[str], max_papers: int = 25) -> dict:
    from app.services.llm_client import llm_enabled

    if not llm_enabled():
        raise RuntimeError(
            "No LLM is available (Ollama not reachable, or model not pulled). "
            "report_generation falls back to a template report with no self-check "
            "in that case, so Report Faithfulness can't be measured — start Ollama first."
        )

    per_question = [_run_one(q, max_papers) for q in questions]
    checked_total = sum(r["checked"] for r in per_question)
    flagged_total = sum(r["flagged"] for r in per_question)

    # Two ways to aggregate: micro (pool all sentences across questions — weights
    # questions with more citations more heavily) and macro (average each
    # question's own rate — every question counts equally regardless of length).
    macro_rates = [
        (r["checked"] - r["flagged"]) / r["checked"] for r in per_question if r["checked"] > 0
    ]

    return {
        "per_question": per_question,
        "checked_total": checked_total,
        "flagged_total": flagged_total,
        "micro_faithfulness": (checked_total - flagged_total) / checked_total if checked_total else None,
        "macro_faithfulness": sum(macro_rates) / len(macro_rates) if macro_rates else None,
        "questions_with_no_citations": sum(1 for r in per_question if r["checked"] == 0),
    }


def print_report(result: dict) -> None:
    print("\n=== Report Faithfulness ===")
    for r in result["per_question"]:
        if r["checked"] == 0:
            print(f"  [{r['generated_by']}] {r['question']} — no cited sentences to check")
            continue
        rate = (r["checked"] - r["flagged"]) / r["checked"]
        print(f"  [{r['generated_by']}] {r['question']}")
        print(f"      {r['checked'] - r['flagged']}/{r['checked']} sentences passed ({rate:.1%})")

    print(f"\ntotal checked: {result['checked_total']}, total flagged: {result['flagged_total']}")
    if result["micro_faithfulness"] is not None:
        print(f"micro faithfulness (pooled):  {result['micro_faithfulness']:.1%}")
        print(f"macro faithfulness (avg/Q):   {result['macro_faithfulness']:.1%}")
    else:
        print("no cited sentences were produced across any question — nothing to score")
    if result["questions_with_no_citations"]:
        print(f"({result['questions_with_no_citations']} question(s) had no single-citation sentences to check)")


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions_file", help="one research question per line; defaults to a built-in sample set")
    parser.add_argument("--max_papers", type=int, default=25)
    parser.add_argument("--json_out", help="optional path to also dump the result as JSON")
    args = parser.parse_args()

    if args.questions_file:
        with open(args.questions_file) as f:
            questions = [line.strip() for line in f if line.strip()]
    else:
        questions = DEFAULT_QUESTIONS

    result = evaluate(questions, args.max_papers)
    print_report(result)
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
