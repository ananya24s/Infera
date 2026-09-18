"""Train the LightGBM relevance/credibility ranker.

This script trains on REAL judged (query, paper) pairs — it does not
fabricate labels. Two supported label sources, chosen with --source:

  csv       A CSV file with columns: query, paper_id, title, abstract, year,
            citation_count, influential_citation_count, is_open_access,
            relevance_label (0-3 graded relevance, e.g. from human judgments
            or a query log with click-through / dwell-time derived grades).

  citation  Weak-supervision from OpenAlex's own citation graph: for a list
            of seed queries, treats a paper's hybrid-search rank position +
            citation count as a noisy relevance proxy. This is documented as
            WEAK supervision (not ground truth) — use --source csv with real
            judgments for a production model.

Usage:
    python -m training.train_ranker --source csv --input judgments.csv --output ./data/ranker.lgb
"""
from __future__ import annotations

import argparse
import asyncio
import csv

import numpy as np


def _features_and_labels_from_csv(path: str) -> tuple[np.ndarray, np.ndarray]:
    from app.ml.ranker import RankFeatures
    from app.services.hybrid_search import HybridIndex
    from app.models.schemas import Paper

    rows_by_query: dict[str, list[dict]] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows_by_query.setdefault(row["query"], []).append(row)

    X, y = [], []
    for query, rows in rows_by_query.items():
        papers = [
            Paper(
                paper_id=r["paper_id"],
                title=r["title"],
                abstract=r.get("abstract", ""),
                year=int(r["year"]) if r.get("year") else None,
                citation_count=int(r.get("citation_count") or 0),
                influential_citation_count=int(r.get("influential_citation_count") or 0),
                is_open_access=r.get("is_open_access", "").lower() in ("1", "true", "yes"),
            )
            for r in rows
        ]
        index = HybridIndex(papers=papers)
        scored = {p.paper_id: (d, s, h) for p, d, s, h in index.search(query, top_k=len(papers))}
        for r in rows:
            dense, sparse, hybrid = scored.get(r["paper_id"], (0.0, 0.0, 0.0))
            paper = next(p for p in papers if p.paper_id == r["paper_id"])
            feats = RankFeatures(
                dense_score=dense,
                sparse_score=sparse,
                hybrid_score=hybrid,
                citation_count=paper.citation_count,
                influential_citation_count=paper.influential_citation_count,
                is_open_access=paper.is_open_access,
                year=paper.year,
            )
            X.append(feats.to_vector())
            y.append(float(r["relevance_label"]))

    return np.array(X), np.array(y)


async def _features_and_labels_from_citation_graph(
    queries: list[str], per_query: int
) -> tuple[np.ndarray, np.ndarray]:
    """Weak supervision: label = min-max normalized rank of (hybrid_score
    combined with log-citation count) within each query's candidate pool.
    This is a noisy proxy, not human judgment — prefer --source csv.
    """
    from app.ml.ranker import RankFeatures
    from app.services import openalex
    from app.services.hybrid_search import HybridIndex

    X, y = [], []
    for query in queries:
        papers = await openalex.search(query, limit=per_query)
        if len(papers) < 3:
            continue
        index = HybridIndex(papers=papers)
        scored = index.search(query, top_k=len(papers))
        citation_component = np.array([np.log1p(p.citation_count) for p, *_ in scored])
        citation_component = citation_component / (citation_component.max() or 1)
        for (paper, dense, sparse, hybrid), cite_norm in zip(scored, citation_component):
            feats = RankFeatures(
                dense_score=dense,
                sparse_score=sparse,
                hybrid_score=hybrid,
                citation_count=paper.citation_count,
                influential_citation_count=paper.influential_citation_count,
                is_open_access=paper.is_open_access,
                year=paper.year,
            )
            X.append(feats.to_vector())
            y.append(0.6 * hybrid + 0.4 * float(cite_norm))

    return np.array(X), np.array(y)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["csv", "citation"], required=True)
    parser.add_argument("--input", help="CSV path (source=csv)")
    parser.add_argument("--queries", help="Path to newline-separated seed queries (source=citation)")
    parser.add_argument("--per_query", type=int, default=30)
    parser.add_argument("--output", default="./data/ranker.lgb")
    args = parser.parse_args()

    if args.source == "csv":
        if not args.input:
            raise SystemExit("--input is required for --source csv")
        X, y = _features_and_labels_from_csv(args.input)
    else:
        if not args.queries:
            raise SystemExit("--queries is required for --source citation")
        queries = [q.strip() for q in open(args.queries) if q.strip()]
        X, y = asyncio.run(_features_and_labels_from_citation_graph(queries, args.per_query))

    if len(X) < 10:
        raise SystemExit(f"Only {len(X)} training examples found — need more labeled data.")

    import lightgbm as lgb
    from app.ml.ranker import FEATURE_NAMES

    split = int(len(X) * 0.85)
    train_set = lgb.Dataset(X[:split], label=y[:split], feature_name=FEATURE_NAMES)
    val_set = lgb.Dataset(X[split:], label=y[split:], reference=train_set)

    booster = lgb.train(
        {"objective": "regression", "metric": "rmse", "learning_rate": 0.05, "num_leaves": 15},
        train_set,
        num_boost_round=200,
        valid_sets=[val_set],
        callbacks=[lgb.early_stopping(20), lgb.log_evaluation(20)],
    )
    booster.save_model(args.output)
    print(f"Saved ranker to {args.output}")
    print(f"Set INFERA_RANKER_PATH={args.output} to use it.")


if __name__ == "__main__":
    main()
