"""Evaluate Retrieval Recall@25 against a hand-labeled gold set (slide 8's
"Retrieval Recall" metric): of the papers a human marked genuinely relevant
for a question, what fraction actually appear in production retrieval's real
top-25 (ResearchRequest.max_papers's default — see app/models/schemas.py)?

Needs a gold set built with training/build_recall_gold_set.py (a wider
candidate pool than 25, hand-labeled "relevant": true/false per candidate —
see that script's docstring and training/data/recall_gold_set.json for the
first labeled question). Recall is computed only against papers a human
judged relevant within the pool that was actually fetched and shown (standard
TREC-style pooling) — it can't account for a relevant paper neither retrieval
attempt ever surfaced.

Usage:
    python -m training.eval_retrieval_recall
    python -m training.eval_retrieval_recall --gold_set training/data/recall_gold_set.json --k 25
"""
from __future__ import annotations

import argparse
import json


def _norm_title(title: str) -> str:
    # Same normalization retrieval.py's own dedup uses, so matching is exact.
    return "".join(c.lower() for c in title if c.isalnum())


def _run_one(entry: dict, k: int) -> dict:
    from app.agents.retrieval import run as retrieval
    from app.models.schemas import SubQuestion
    from app.orchestrator.state import ResearchState

    question = entry["question"]
    relevant_titles = {_norm_title(c["title"]) for c in entry["candidates"] if c["relevant"]}

    state = ResearchState(question=question, max_papers=k)
    state.sub_questions = [SubQuestion(id="sq1", text=question)]
    retrieval(state)
    retrieved_titles = {_norm_title(p.title) for p in state.papers}

    found = relevant_titles & retrieved_titles
    return {
        "question": question,
        "relevant_total": len(relevant_titles),
        "relevant_found": len(found),
        "retrieved": len(retrieved_titles),
    }


def evaluate(gold_set: list[dict], k: int) -> dict:
    per_question = [_run_one(entry, k) for entry in gold_set]
    total_relevant = sum(r["relevant_total"] for r in per_question)
    total_found = sum(r["relevant_found"] for r in per_question)
    macro_rates = [r["relevant_found"] / r["relevant_total"] for r in per_question if r["relevant_total"] > 0]

    return {
        "k": k,
        "per_question": per_question,
        "micro_recall": total_found / total_relevant if total_relevant else None,
        "macro_recall": sum(macro_rates) / len(macro_rates) if macro_rates else None,
    }


def print_report(result: dict) -> None:
    k = result["k"]
    print(f"\n=== Retrieval Recall@{k} ===")
    for r in result["per_question"]:
        if r["relevant_total"] == 0:
            print(f"  {r['question']} — no relevant papers labeled, skipped")
            continue
        rate = r["relevant_found"] / r["relevant_total"]
        print(f"  {r['question']}")
        print(f"      {r['relevant_found']}/{r['relevant_total']} relevant papers retrieved in top {k} ({rate:.1%})")

    if result["micro_recall"] is not None:
        print(f"\nmicro recall@{k} (pooled):  {result['micro_recall']:.1%}")
        print(f"macro recall@{k} (avg/Q):   {result['macro_recall']:.1%}")
    else:
        print("\nno labeled-relevant papers across any question — nothing to score")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold_set", default="./training/data/recall_gold_set.json")
    parser.add_argument("--k", type=int, default=25, help="matches ResearchRequest.max_papers's default")
    parser.add_argument("--json_out")
    args = parser.parse_args()

    with open(args.gold_set) as f:
        gold_set = json.load(f)

    unlabeled = [c["n"] for e in gold_set for c in e["candidates"] if c["relevant"] is None]
    if unlabeled:
        raise RuntimeError(f"{len(unlabeled)} candidate(s) still have \"relevant\": null — label them before scoring")

    result = evaluate(gold_set, args.k)
    print_report(result)
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
