"""LLM access, scoped deliberately narrow.

Used only for: (1) splitting a research question into sub-questions,
(2) segmenting a paper abstract into atomic candidate claims, and
(3) drafting/revising report prose. It never scores relevance, credibility,
entailment, or consensus — those come from the trained ranker, NLI model, and
HDBSCAN clustering respectively.

Providers (INFERA_LLM_PROVIDER):
  auto       (default) Anthropic if ANTHROPIC_API_KEY is set, else a local
             Ollama server if one is reachable and has the model, else none.
  ollama     Local model via Ollama — free, no key, runs on your machine.
  anthropic  Claude via the Anthropic API (paid, needs a key).
  none       No LLM; agents use their rule-based/template fallbacks.
"""
from __future__ import annotations

import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_OLLAMA_PROBE_TTL_S = 30.0
_ollama_probe: tuple[float, bool] | None = None  # (checked_at, available)


def _ollama_available() -> bool:
    """True if the Ollama server is up and has the configured model pulled.
    Cached briefly so the per-request `llm_enabled()` calls stay cheap."""
    global _ollama_probe
    now = time.monotonic()
    if _ollama_probe and now - _ollama_probe[0] < _OLLAMA_PROBE_TTL_S:
        return _ollama_probe[1]

    settings = get_settings()
    available = False
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=1.5)
        resp.raise_for_status()
        wanted = settings.ollama_model
        names = {m.get("name", "") for m in resp.json().get("models", [])}
        # "qwen2.5:7b" may be listed as "qwen2.5:7b"; a bare "qwen2.5" as "qwen2.5:latest".
        available = wanted in names or f"{wanted}:latest" in names
        if not available:
            logger.warning(
                "Ollama is running but model %r isn't pulled (have: %s). Run: ollama pull %s",
                wanted, sorted(names) or "none", wanted,
            )
    except httpx.HTTPError:
        available = False

    _ollama_probe = (now, available)
    return available


def active_provider() -> str:
    """Resolve the configured provider to one of: ollama | anthropic | none."""
    settings = get_settings()
    provider = settings.llm_provider
    if provider == "anthropic":
        return "anthropic" if settings.anthropic_api_key else "none"
    if provider == "ollama":
        return "ollama" if _ollama_available() else "none"
    if provider == "none":
        return "none"
    # auto
    if settings.anthropic_api_key:
        return "anthropic"
    if _ollama_available():
        return "ollama"
    return "none"


def llm_enabled() -> bool:
    return active_provider() != "none"


def llm_description() -> str:
    provider = active_provider()
    if provider == "ollama":
        return f"ollama/{get_settings().ollama_model}"
    if provider == "anthropic":
        return f"anthropic/{get_settings().llm_model}"
    return "none (rule-based fallbacks)"


async def complete(system: str, prompt: str, max_tokens: int = 1024) -> str:
    provider = active_provider()
    if provider == "ollama":
        return await _complete_ollama(system, prompt, max_tokens)
    if provider == "anthropic":
        return await _complete_anthropic(system, prompt, max_tokens)
    raise RuntimeError("No LLM available (provider resolved to 'none').")


async def _complete_ollama(system: str, prompt: str, max_tokens: int) -> str:
    settings = get_settings()
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        # Low temperature: these are extraction/revision tasks, not creative ones.
        "options": {"num_predict": max_tokens, "temperature": 0.2},
    }
    # Generous timeout: a 7B model on a laptop can take a while for long outputs.
    async with httpx.AsyncClient(timeout=settings.ollama_timeout_s) as client:
        resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def _complete_anthropic(system: str, prompt: str, max_tokens: int) -> str:
    import anthropic

    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")
