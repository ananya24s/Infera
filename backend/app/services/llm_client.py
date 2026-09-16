"""LLM access, scoped deliberately narrow.

Used only for: (1) splitting a research question into sub-questions,
(2) segmenting a paper abstract into atomic candidate claims, and
(3) drafting/revising report prose. It never scores relevance, credibility,
entailment, or consensus — those come from the trained ranker, NLI model, and
HDBSCAN clustering respectively.
"""
from __future__ import annotations

from app.config import get_settings


async def complete(system: str, prompt: str, max_tokens: int = 1024) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. The LLM is only used for phrasing "
            "(sub-question drafting, claim segmentation, report prose) — set the "
            "key to enable it, or supply INFERA_LLM_PROVIDER=none to run agents "
            "in rule-based fallback mode."
        )

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def llm_enabled() -> bool:
    return get_settings().anthropic_api_key is not None
