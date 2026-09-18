"""NLI-based claim verification.

Wraps a HuggingFace sequence-classification NLI checkpoint and maps its
entailment/neutral/contradiction output onto SUPPORTS/NOT_ENOUGH_INFO/REFUTES,
matching the SciFact label set. Default checkpoint is a FEVER-trained model;
run backend/training/train_nli.py against the SciFact dataset and point
INFERA_NLI_MODEL at the resulting checkpoint for domain-specific claim
verification against scientific abstracts.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.config import get_settings
from app.models.schemas import VerificationLabel


@dataclass
class NLIResult:
    label: VerificationLabel
    confidence: float


@lru_cache
def _pipeline():
    from transformers import pipeline

    settings = get_settings()
    return pipeline("text-classification", model=settings.nli_model_name, top_k=None)


def warmup() -> None:
    """Force the NLI checkpoint to load now rather than on the first request."""
    _pipeline()


_LABEL_MAP = {
    "entailment": VerificationLabel.SUPPORTS,
    "supports": VerificationLabel.SUPPORTS,
    "neutral": VerificationLabel.NOT_ENOUGH_INFO,
    "not_enough_info": VerificationLabel.NOT_ENOUGH_INFO,
    "contradiction": VerificationLabel.REFUTES,
    "refutes": VerificationLabel.REFUTES,
}


def verify(premise: str, hypothesis: str) -> NLIResult:
    """premise = source evidence sentence(s); hypothesis = extracted claim."""
    clf = _pipeline()
    # Most NLI checkpoints expect "premise </s></s> hypothesis" style pairing;
    # the HF pipeline handles this via text_pair.
    outputs = clf({"text": premise, "text_pair": hypothesis})
    if outputs and isinstance(outputs[0], list):
        outputs = outputs[0]

    best = max(outputs, key=lambda o: o["score"])
    raw_label = best["label"].lower()
    label = _LABEL_MAP.get(raw_label, VerificationLabel.NOT_ENOUGH_INFO)
    return NLIResult(label=label, confidence=float(best["score"]))
