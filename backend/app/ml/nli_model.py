"""NLI-based claim verification.

Wraps a HuggingFace sequence-classification NLI checkpoint and maps its
entailment/neutral/contradiction output onto SUPPORTS/NOT_ENOUGH_INFO/REFUTES,
matching the SciFact label set. Default checkpoint is a FEVER-trained model;
run backend/training/train_nli.py against the SciFact dataset and point
INFERA_NLI_MODEL at the resulting checkpoint for domain-specific claim
verification against scientific abstracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from app.config import get_settings
from app.models.schemas import VerificationLabel


@dataclass
class NLIResult:
    label: VerificationLabel
    confidence: float
    # Probability of each label — needed to pick the *least neutral* evidence
    # sentence in an abstract, not just the argmax label.
    probs: dict[VerificationLabel, float] = field(default_factory=dict)

    def prob(self, label: VerificationLabel) -> float:
        return self.probs.get(label, 0.0)


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


_BATCH_SIZE = 16


def _to_result(outputs: list[dict]) -> NLIResult:
    probs = {v: 0.0 for v in VerificationLabel}
    for o in outputs:
        label = _LABEL_MAP.get(o["label"].lower(), VerificationLabel.NOT_ENOUGH_INFO)
        probs[label] += float(o["score"])
    best = max(probs, key=probs.get)
    return NLIResult(label=best, confidence=probs[best], probs=probs)


def verify_batch(pairs: list[tuple[str, str]]) -> list[NLIResult]:
    """pairs = [(premise, hypothesis), ...]. premise is the evidence; it's the
    side that gets truncated if too long, never the hypothesis."""
    if not pairs:
        return []
    clf = _pipeline()
    inputs = [{"text": premise, "text_pair": hypothesis} for premise, hypothesis in pairs]
    raw = clf(inputs, batch_size=_BATCH_SIZE, truncation="only_first", max_length=512)
    return [_to_result(o if isinstance(o, list) else [o]) for o in raw]


def verify(premise: str, hypothesis: str) -> NLIResult:
    """Single-pair convenience wrapper. premise = evidence; hypothesis = the claim being checked."""
    return verify_batch([(premise, hypothesis)])[0]
