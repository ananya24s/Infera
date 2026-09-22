"""Shared fakes: a keyword-driven stand-in for the NLI model, so agent logic
is tested quickly and deterministically without loading any checkpoint."""
from __future__ import annotations

from app.ml.nli_model import NLIResult
from app.models.schemas import VerificationLabel as L


def fake_verify_batch(pairs: list[tuple[str, str]]) -> list[NLIResult]:
    out = []
    for premise, _hypothesis in pairs:
        p = premise.lower()
        if "no significant" in p or "did not" in p:
            probs = {L.SUPPORTS: 0.02, L.REFUTES: 0.95, L.NOT_ENOUGH_INFO: 0.03}
        elif "improved" in p:
            probs = {L.SUPPORTS: 0.93, L.REFUTES: 0.02, L.NOT_ENOUGH_INFO: 0.05}
        else:
            probs = {L.SUPPORTS: 0.05, L.REFUTES: 0.05, L.NOT_ENOUGH_INFO: 0.90}
        label = max(probs, key=probs.get)
        out.append(NLIResult(label=label, confidence=probs[label], probs=probs))
    return out
