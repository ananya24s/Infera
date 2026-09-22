"""Thin client for the OpenAlex Works API — free, keyless, no signup.

Chosen over Semantic Scholar as a retrieval source because unauthenticated
S2 access is aggressively (in practice, unusably) rate-limited, and getting
a key requires an institutional/edu email. OpenAlex needs no key at all,
has no meaningful rate-limit wall, and covers more ground than S2 —
including the biomedical/nutrition journals arXiv doesn't index. Setting
INFERA_OPENALEX_CONTACT_EMAIL (any email, no verification) moves requests
into OpenAlex's faster "polite pool"; it's optional.
"""
from __future__ import annotations

import asyncio

import httpx

from app.config import get_settings
from app.models.schemas import Paper

BASE_URL = "https://api.openalex.org/works"

SELECT_FIELDS = (
    "id,display_name,abstract_inverted_index,authorships,publication_year,"
    "primary_location,cited_by_count,open_access,referenced_works,doi"
)

_MAX_REFERENCES_PER_PAPER = 50

_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.5


def _short_id(openalex_url: str) -> str:
    return openalex_url.rsplit("/", 1)[-1]


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex ships abstracts as {word: [positions]} to dodge copyright
    concerns over reproducing full text verbatim; rebuild the plain string."""
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def _sanitize_query(query: str) -> str:
    # OpenAlex's default search treats "?" and "*" as wildcard operators
    # (400s on them outside search.exact), and research questions routinely
    # end in "?" — strip them rather than have every question-phrased query fail.
    return query.replace("?", " ").replace("*", " ").strip()


async def search(query: str, limit: int = 20) -> list[Paper]:
    settings = get_settings()
    params: dict[str, str | int] = {
        "search": _sanitize_query(query),
        "per-page": limit,
        "select": SELECT_FIELDS,
    }
    if settings.openalex_contact_email:
        params["mailto"] = settings.openalex_contact_email

    async with httpx.AsyncClient(timeout=settings.request_timeout_s, follow_redirects=True) as client:
        data = await _get_with_retry(client, params)

    papers: list[Paper] = []
    for item in data.get("results", []):
        title = item.get("display_name")
        openalex_id = item.get("id")
        if not title or not openalex_id:
            continue

        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        open_access = item.get("open_access") or {}
        references = [
            f"openalex:{_short_id(ref)}"
            for ref in (item.get("referenced_works") or [])[:_MAX_REFERENCES_PER_PAPER]
        ]

        papers.append(
            Paper(
                paper_id=f"openalex:{_short_id(openalex_id)}",
                title=title,
                abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
                authors=[
                    (a.get("author") or {}).get("display_name", "")
                    for a in item.get("authorships") or []
                ],
                year=item.get("publication_year"),
                venue=source.get("display_name"),
                citation_count=item.get("cited_by_count") or 0,
                influential_citation_count=0,  # OpenAlex has no direct equivalent to S2's metric
                is_open_access=bool(open_access.get("is_oa")),
                url=item.get("doi") or primary_location.get("landing_page_url"),
                source="openalex",
                references=references,
            )
        )
    return papers


async def _get_with_retry(client: httpx.AsyncClient, params: dict) -> dict:
    for attempt in range(_MAX_RETRIES):
        resp = await client.get(BASE_URL, params=params)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp.json()
        if attempt < _MAX_RETRIES - 1:
            retry_after = resp.headers.get("retry-after")
            delay = float(retry_after) if retry_after else _BASE_BACKOFF_S * (2**attempt)
            await asyncio.sleep(delay)
    resp.raise_for_status()  # exhausted retries; surface the 429 as an error
    return resp.json()
