"""Fine-tune an NLI checkpoint on SciFact (+ optionally FEVER) for scientific
claim verification.

Usage:
    python -m training.train_nli --output_dir ./data/scifact-nli --epochs 3

Loads the real `allenai/scifact` dataset from HuggingFace Datasets (claim +
cited_doc_id + evidence label: SUPPORT/CONTRADICT/NOINFO), maps it onto the
SUPPORTS/REFUTES/NOT_ENOUGH_INFO label set used throughout Infera, and
fine-tunes a sequence-classification model (default: the same base as
app/config.py's INFERA_NLI_MODEL). Point INFERA_NLI_MODEL at --output_dir
once training completes to switch the live pipeline to the fine-tuned model.
"""
from __future__ import annotations

import argparse

LABEL_MAP = {
    "SUPPORT": "entailment",
    "CONTRADICT": "contradiction",
    "NOINFO": "neutral",
}
LABEL_LIST = ["entailment", "neutral", "contradiction"]


def build_examples(split):
    from datasets import load_dataset

    scifact = load_dataset("allenai/scifact", "claims", split=split)
    corpus = {row["doc_id"]: row for row in load_dataset("allenai/scifact", "corpus", split="train")}

    examples = []
    for row in scifact:
        cited = row.get("cited_doc_ids") or []
        evidence = row.get("evidence") or {}
        if not cited:
            continue
        for doc_id in cited:
            doc = corpus.get(doc_id)
            if not doc:
                continue
            premise = " ".join(doc.get("abstract", []))
            doc_evidence = evidence.get(str(doc_id)) or evidence.get(doc_id)
            label = "NOINFO"
            if doc_evidence:
                label = doc_evidence[0].get("label", "NOINFO")
            examples.append(
                {"premise": premise, "hypothesis": row["claim"], "label": LABEL_MAP[label]}
            )
    return examples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
    parser.add_argument("--output_dir", default="./data/scifact-nli")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-5)
    args = parser.parse_args()

    import numpy as np
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    train_examples = build_examples("train")
    val_examples = build_examples("validation")
    print(f"train={len(train_examples)} val={len(val_examples)}")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model, num_labels=len(LABEL_LIST), ignore_mismatched_sizes=True
    )
    model.config.id2label = dict(enumerate(LABEL_LIST))
    model.config.label2id = {l: i for i, l in enumerate(LABEL_LIST)}

    def tokenize(batch):
        enc = tokenizer(batch["premise"], batch["hypothesis"], truncation=True, max_length=256)
        enc["labels"] = [LABEL_LIST.index(l) for l in batch["label"]]
        return enc

    train_ds = Dataset.from_list(train_examples).map(tokenize, batched=True)
    val_ds = Dataset.from_list(val_examples).map(tokenize, batched=True)

    def compute_metrics(eval_pred):
        preds = np.argmax(eval_pred.predictions, axis=1)
        acc = (preds == eval_pred.label_ids).mean()
        return {"accuracy": float(acc)}

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved fine-tuned checkpoint to {args.output_dir}")
    print(f"Set INFERA_NLI_MODEL={args.output_dir} to use it.")


if __name__ == "__main__":
    main()
