"""Runtime configuration, loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

# Must run before any os.getenv() calls below (including the ones baked into
# Settings' field defaults, which execute once at class-definition time).
# Real environment variables (e.g. set by the host in production) still win —
# load_dotenv() never overrides an already-set var.
load_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


class Settings(BaseModel):
    # External retrieval APIs — both are free and keyless.
    arxiv_base_url: str = "https://export.arxiv.org/api/query"
    # Optional: any email, no verification. Moves OpenAlex requests into their
    # faster "polite pool" — see https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
    # `or None` matters: a blank line in .env (INFERA_OPENALEX_CONTACT_EMAIL=)
    # loads as "", not absent — normalize so downstream `is not None` checks work.
    openalex_contact_email: str | None = os.getenv("INFERA_OPENALEX_CONTACT_EMAIL") or None

    # LLM used ONLY for phrasing help (report drafting) and claim segmentation assistance.
    # Judgments (ranking/verification/consensus) never come from this model.
    # auto | ollama | anthropic | none — see app/services/llm_client.py
    llm_provider: str = (os.getenv("INFERA_LLM_PROVIDER") or "auto").lower()
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None
    llm_model: str = os.getenv("INFERA_LLM_MODEL") or "claude-sonnet-5"
    # Local, free LLM via Ollama (https://ollama.com).
    ollama_base_url: str = os.getenv("INFERA_OLLAMA_URL") or "http://localhost:11434"
    ollama_model: str = os.getenv("INFERA_OLLAMA_MODEL") or "qwen2.5:7b"
    ollama_timeout_s: float = _env_float("INFERA_OLLAMA_TIMEOUT_S", 180.0)
    # How long Ollama keeps the model in RAM after its last request. Kept short on
    # purpose: a 7B model resident during CPU-bound NLI verification pushes a 16GB
    # machine into swap, and verification (which doesn't use the LLM) slows ~10x+.
    ollama_keep_alive: str = os.getenv("INFERA_OLLAMA_KEEP_ALIVE") or "20s"

    # Trained-model checkpoints
    # `or default` matters here too (see the comment on openalex_contact_email
    # above): a blank line in .env (e.g. INFERA_EMBEDDING_MODEL=) loads as ""
    # rather than absent, and os.getenv's positional default only applies when
    # the var is entirely unset — plain positional defaults here would load
    # SentenceTransformer("") / an empty NLI model id and fail in confusing
    # ways far from this file (reproduced: sentence-transformers silently
    # leaves its internal module empty, "'NoneType' object has no attribute
    # 'parameters'" three layers down in a completely unrelated warmup call).
    nli_model_name: str = os.getenv("INFERA_NLI_MODEL") or (
        # Default: a strong FEVER/fact-verification-trained NLI checkpoint.
        # Fine-tune on SciFact via backend/training/train_nli.py and point this at the
        # resulting checkpoint directory for domain-specific scientific claim verification.
        "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    )
    embedding_model_name: str = os.getenv("INFERA_EMBEDDING_MODEL") or "sentence-transformers/all-MiniLM-L6-v2"
    ranker_model_path: str = os.getenv("INFERA_RANKER_PATH") or "backend/training/data/ranker.lgb"

    max_retrieval_per_query: int = 40
    max_claims_per_paper: int = 6
    request_timeout_s: float = 20.0

    # Comma-separated list of allowed frontend origins for CORS. Defaults to
    # local dev; set INFERA_ALLOWED_ORIGINS in production to your deployed
    # frontend's real origin(s), e.g. "https://infera.example.com".
    allowed_origins: list[str] = (
        os.getenv("INFERA_ALLOWED_ORIGINS") or "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")

    # Per-client-IP cap on /api/research calls (each one is compute-heavy and,
    # if ANTHROPIC_API_KEY is set, also costs real money) — deliberately
    # conservative defaults for a small/demo deployment.
    rate_limit_max_requests: int = _env_int("INFERA_RATE_LIMIT_MAX_REQUESTS", 10)
    rate_limit_window_s: float = _env_float("INFERA_RATE_LIMIT_WINDOW_S", 3600.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
