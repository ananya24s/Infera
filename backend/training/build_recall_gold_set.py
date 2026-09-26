"""Build a Retrieval Recall gold set: for one research question, fetch a wide
candidate pool (bigger than production's max_papers=25) so recall against it
isn't trivially ~100%, then let a human mark which candidates are genuinely
relevant. Standard TREC-style pooling: anything never surfaced by any query
variant is assumed non-relevant, since exhaustively checking every paper that
exists is impossible.

Appends one {question, candidates} entry to a gold-set file (a JSON list, one
entry per labeled question — see training/data/recall_gold_set.json for the
first one) so eval_retrieval_recall.py can score against several questions.

This script only fetches and prints candidates for labeling — it doesn't
label them itself. After running it, edit the appended entry's "relevant"
fields (true/false) by hand, or set them programmatically as this project's
first pass did (see project notes) — the point is a human decision, not this
script's.

Usage:
    python -m training.build_recall_gold_set "Does creatine improve memory?" --pool_size 40
"""
from __future__ import annotations

import argparse
import json
import os


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--pool_size", type=int, default=40)
    parser.add_argument("--out", default="./training/data/recall_gold_set.json")
    args = parser.parse_args()

    from app.agents.retrieval import run as retrieval
    from app.models.schemas import SubQuestion
    from app.orchestrator.state import ResearchState

    state = ResearchState(question=args.question, max_papers=args.pool_size)
    state.sub_questions = [SubQuestion(id="sq1", text=args.question)]
    retrieval(state)

    candidates = [
        {"n": i + 1, "paper_id": p.paper_id, "title": p.title, "year": p.year,
         "abstract": p.abstract, "relevant": None}
        for i, p in enumerate(state.papers)
    ]
    entry = {"question": args.question, "candidates": candidates}

    gold_set = []
    if os.path.exists(args.out):
        with open(args.out) as f:
            gold_set = json.load(f)
    gold_set.append(entry)
    with open(args.out, "w") as f:
        json.dump(gold_set, f, indent=2)

    print(f"Fetched {len(candidates)} candidates for: {args.question!r}")
    print(f"Appended to {args.out} as entry {len(gold_set)} (each candidate has \"relevant\": null, to be filled in)\n")
    for c in candidates:
        snippet = (c["abstract"][:140] + "...") if len(c["abstract"]) > 140 else c["abstract"]
        print(f"[{c['n']:>2}] {c['title']} ({c['year'] or 'n.d.'})")
        print(f"     {snippet}")


if __name__ == "__main__":
    main()
