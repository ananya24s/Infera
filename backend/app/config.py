"""Runtime configuration, loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    # External retrieval APIs — both are free and keyless.
    arxiv_base_url: str = "https://export.arxiv.org/api/query"
    # Optional: any email, no verification. Moves OpenAlex requests into their
    # faster "polite pool" — see https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
    openalex_contact_email: str | None = os.getenv("INFERA_OPENALEX_CONTACT_EMAIL")

    # LLM used ONLY for phrasing help (report drafting) and claim segmentation assistance.
    # Judgments (ranking/verification/consensus) never come from this model.
    llm_provider: str = os.getenv("INFERA_LLM_PROVIDER", "anthropic")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    llm_model: str = os.getenv("INFERA_LLM_MODEL", "claude-sonnet-5")

    # Trained-model checkpoints
    nli_model_name: str = os.getenv(
        "INFERA_NLI_MODEL",
        # Default: a strong FEVER/fact-verification-trained NLI checkpoint.
        # Fine-tune on SciFact via backend/training/train_nli.py and point this at the
        # resulting checkpoint directory for domain-specific scientific claim verification.
        "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
    )
    embedding_model_name: str = os.getenv(
        "INFERA_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    ranker_model_path: str = os.getenv(
        "INFERA_RANKER_PATH", "backend/training/data/ranker.lgb"
    )

    max_retrieval_per_query: int = 40
    max_claims_per_paper: int = 6
    request_timeout_s: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
