"""Loads the real SciFact dataset (https://github.com/allenai/scifact) from the
local JSONL release — HuggingFace's `allenai/scifact` loader script is no longer
usable (HF dropped support for dataset loading scripts), so this reads the
official archive directly.

Fetch it once with:
    curl -o data.tar.gz https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz
    tar xzf data.tar.gz -C training/data/scifact_raw && rm data.tar.gz

Each SciFact claim cites one or more "candidate" documents. For a cited doc:
  - if SciFact records evidence sentences + a label (SUPPORT/CONTRADICT), that's
    the doc's stance;
  - if a doc is cited but has NO evidence entry, that's a NOINFO pair (SciFact's
    own construction — a topically related but non-evidentiary distractor).

The premise is the full abstract (not just the cited sentences): that matches
exactly how Infera verifies claims in production (whole-abstract vs. hypothesis),
so training/eval distribution matches the actual use case.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "scifact_raw" / "data"

_SCIFACT_TO_NLI = {
    "SUPPORT": "entailment",
    "CONTRADICT": "contradiction",
    "NOINFO": "neutral",
}


@dataclass
class Example:
    premise: str
    hypothesis: str
    label: str  # entailment | neutral | contradiction
    claim_id: int
    doc_id: int


def _load_corpus() -> dict[int, str]:
    corpus = {}
    with open(DATA_DIR / "corpus.jsonl") as f:
        for line in f:
            doc = json.loads(line)
            corpus[doc["doc_id"]] = " ".join(doc["abstract"])
    return corpus


def load_examples(split: str) -> list[Example]:
    """split: 'train' or 'dev' (SciFact's 'test' split ships without labels —
    it's for the public leaderboard — so it can't be used here)."""
    if split not in ("train", "dev"):
        raise ValueError(f"SciFact has labels for 'train'/'dev' only, not {split!r}")
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"{DATA_DIR} not found. Fetch the dataset first — see this module's docstring."
        )

    corpus = _load_corpus()
    examples: list[Example] = []
    with open(DATA_DIR / f"claims_{split}.jsonl") as f:
        for line in f:
            claim = json.loads(line)
            evidence = claim.get("evidence") or {}
            for doc_id in claim.get("cited_doc_ids") or []:
                abstract = corpus.get(doc_id)
                if not abstract:
                    continue
                doc_evidence = evidence.get(str(doc_id))
                label = _SCIFACT_TO_NLI[doc_evidence[0]["label"] if doc_evidence else "NOINFO"]
                examples.append(
                    Example(
                        premise=abstract,
                        hypothesis=claim["claim"],
                        label=label,
                        claim_id=claim["id"],
                        doc_id=doc_id,
                    )
                )
    return examples
