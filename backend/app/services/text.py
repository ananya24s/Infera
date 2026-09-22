"""Small text helpers shared by the verification and report agents."""
from __future__ import annotations

import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(\[])")


def split_sentences(text: str, min_words: int = 4, max_sentences: int = 14) -> list[str]:
    """Split an abstract into sentences. Drops fragments (section labels like
    "BACKGROUND:") and caps the count so one very long abstract can't dominate
    the NLI workload."""
    sentences = [s.strip() for s in _SENTENCE_BOUNDARY.split(text.strip())]
    return [s for s in sentences if len(s.split()) >= min_words][:max_sentences]
