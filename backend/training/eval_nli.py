"""Evaluate an NLI checkpoint on real SciFact dev-set claim verification.

Standalone from the live app (loads whatever --model you point it at directly,
not through app.config), so it can score the current default checkpoint and a
freshly fine-tuned one side by side without restarting anything.

Usage:
    python -m training.eval_nli --model MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
    python -m training.eval_nli --model ./data/scifact-nli
"""
from __future__ import annotations

import argparse
import json

LABELS = ["entailment", "neutral", "contradiction"]


def evaluate(model_path: str, split: str = "dev", batch_size: int = 16, max_length: int = 256) -> dict:
    from transformers import pipeline

    from training.scifact_data import load_examples

    examples = load_examples(split)
    clf = pipeline("text-classification", model=model_path, top_k=None)

    inputs = [{"text": e.premise, "text_pair": e.hypothesis} for e in examples]
    raw = clf(inputs, batch_size=batch_size, truncation="only_first", max_length=max_length)

    preds = []
    for scores in raw:
        best = max(scores, key=lambda o: o["score"])
        preds.append(best["label"].lower())

    gold = [e.label for e in examples]
    return score(gold, preds)


def score(gold: list[str], preds: list[str]) -> dict:
    from sklearn.metrics import classification_report, confusion_matrix

    report = classification_report(gold, preds, labels=LABELS, output_dict=True, zero_division=0)
    matrix = confusion_matrix(gold, preds, labels=LABELS)
    return {
        "n": len(gold),
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "per_class": {label: report[label] for label in LABELS},
        "confusion_matrix": {"labels": LABELS, "matrix": matrix.tolist()},
    }


def print_report(name: str, result: dict) -> None:
    print(f"\n=== {name} ===")
    print(f"n={result['n']}  accuracy={result['accuracy']:.3f}  macro_f1={result['macro_f1']:.3f}")
    print(f"{'label':<14}{'precision':>10}{'recall':>10}{'f1':>10}{'support':>10}")
    for label, m in result["per_class"].items():
        print(f"{label:<14}{m['precision']:>10.3f}{m['recall']:>10.3f}{m['f1-score']:>10.3f}{int(m['support']):>10}")
    print("confusion matrix (rows=gold, cols=predicted):", LABELS)
    for label, row in zip(LABELS, result["confusion_matrix"]["matrix"]):
        print(f"  {label:<14}{row}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--split", default="dev")
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--json_out", help="optional path to also dump the result as JSON")
    args = parser.parse_args()

    result = evaluate(args.model, args.split, args.batch_size)
    print_report(args.model, result)
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump({"model": args.model, "split": args.split, **result}, f, indent=2)


if __name__ == "__main__":
    main()
