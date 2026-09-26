"""Fine-tune an NLI checkpoint on the real SciFact dataset for scientific
claim verification.

Usage:
    python -m training.train_nli --output_dir ./data/scifact-nli --epochs 4

Uses training.scifact_data (the local SciFact release — see that module's
docstring for how to fetch it) and fine-tunes a sequence-classification model
on entailment/neutral/contradiction, keeping the label scheme the live
pipeline already expects (app/ml/nli_model.py), so the output directory is a
drop-in replacement: point INFERA_NLI_MODEL at it and nothing else changes.
"""
from __future__ import annotations

import argparse

from training.scifact_data import Example, load_examples

LABEL_LIST = ["entailment", "neutral", "contradiction"]


def _to_hf_dataset(examples: list[Example]):
    from datasets import Dataset

    return Dataset.from_list(
        [{"premise": e.premise, "hypothesis": e.hypothesis, "label": e.label} for e in examples]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
    parser.add_argument("--output_dir", default="./data/scifact-nli")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--max_steps", type=int, default=-1, help="override epochs with a hard step cap (smoke tests)")
    args = parser.parse_args()

    import numpy as np
    import torch
    from torch import nn
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    train_examples = load_examples("train")
    val_examples = load_examples("dev")
    print(f"train={len(train_examples)} val={len(val_examples)}")

    # SciFact's train split is skewed toward entailment/neutral and has roughly
    # half as many contradiction examples (reproduced: 370/355/194 for
    # entailment/neutral/contradiction) — training with plain cross-entropy
    # taught the model to under-predict contradiction, regressing REFUTES
    # accuracy even as overall accuracy improved. Inverse-frequency class
    # weights counteract that by penalizing contradiction mistakes more.
    label_counts = np.array([sum(e.label == label for e in train_examples) for label in LABEL_LIST])
    class_weights = torch.tensor(len(train_examples) / (len(LABEL_LIST) * label_counts), dtype=torch.float32)
    print(f"class weights ({LABEL_LIST}): {class_weights.tolist()}")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model, num_labels=len(LABEL_LIST), ignore_mismatched_sizes=True
    )
    # `ignore_mismatched_sizes` only reinitializes the classifier head when its
    # shape differs from ours — since most 3-way NLI checkpoints already have 3
    # labels, the shape matches and the *pretrained* head weights are kept as-is.
    # Those weights are ordered however that checkpoint's config says (often NOT
    # entailment/neutral/contradiction — cross-encoder/nli-deberta-v3-xsmall is
    # contradiction/entailment/neutral). Silently relabeling them to our order
    # scrambles a working head into a broken one (reproduced: 1-epoch accuracy
    # dropped to 0.31, near-random, until this fix). Force a fresh head instead
    # so it's trained from scratch on SciFact with our label order — the encoder
    # underneath still keeps all its pretrained NLI/FEVER/ANLI knowledge.
    for name, module in model.named_modules():
        if name.endswith("classifier") and isinstance(module, torch.nn.Linear):
            module.reset_parameters()
    model.config.id2label = dict(enumerate(LABEL_LIST))
    model.config.label2id = {label: i for i, label in enumerate(LABEL_LIST)}

    def tokenize(batch):
        enc = tokenizer(
            batch["premise"], batch["hypothesis"], truncation="only_first", max_length=args.max_length
        )
        enc["labels"] = [LABEL_LIST.index(l) for l in batch["label"]]
        return enc

    remove_cols = ["premise", "hypothesis", "label"]
    train_ds = _to_hf_dataset(train_examples).map(tokenize, batched=True, remove_columns=remove_cols)
    val_ds = _to_hf_dataset(val_examples).map(tokenize, batched=True, remove_columns=remove_cols)

    steps_per_epoch = -(-len(train_examples) // args.batch_size)  # ceil
    total_steps = steps_per_epoch * args.epochs
    warmup_steps = max(10, int(0.1 * total_steps))

    def compute_metrics(eval_pred):
        from sklearn.metrics import f1_score

        preds = np.argmax(eval_pred.predictions, axis=1)
        acc = (preds == eval_pred.label_ids).mean()
        macro_f1 = f1_score(eval_pred.label_ids, preds, average="macro")
        return {"accuracy": float(acc), "macro_f1": float(macro_f1)}

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        # DeBERTa-v3's disentangled attention produces NaN gradients on Apple's
        # MPS backend (reproduced: loss collapses to 0/nan within the first
        # epoch) — force CPU, which is slower but numerically correct.
        use_cpu=True,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        warmup_steps=warmup_steps,
        weight_decay=0.01,
        # A --max_steps smoke test won't run long enough to hit an epoch
        # boundary, so skip eval/save/best-model-tracking entirely then —
        # otherwise load_best_model_at_end errors with no checkpoint saved.
        eval_strategy="no" if args.max_steps > 0 else "epoch",
        save_strategy="no" if args.max_steps > 0 else "epoch",
        save_total_limit=2,
        load_best_model_at_end=args.max_steps <= 0,
        metric_for_best_model="macro_f1" if args.max_steps <= 0 else None,
        logging_steps=1 if args.max_steps > 0 else 20,
        report_to=[],
    )

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            weight = class_weights.to(device=outputs.logits.device, dtype=outputs.logits.dtype)
            loss = nn.functional.cross_entropy(outputs.logits, labels, weight=weight)
            return (loss, outputs) if return_outputs else loss

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    if args.max_steps > 0:
        print(f"\nSmoke test done ({args.max_steps} steps) — nothing saved, this run was just for timing.")
        return

    metrics = trainer.evaluate()
    print("Final eval:", metrics)

    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"\nSaved fine-tuned checkpoint to {args.output_dir}")
    print(f"Set INFERA_NLI_MODEL={args.output_dir} to use it.")


if __name__ == "__main__":
    main()
