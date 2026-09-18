"""Thin client for the Semantic Scholar Graph API (no key required for light use).

The unauthenticated tier is aggressively rate-limited (429s under any real
concurrency, e.g. one call per sub-question), so requests are retried with
backoff before giving up.
"""
from __future__ import annotations

import asyncio

import httpx

from app.config import get_settings
from app.models.schemas import Paper

FIELDS = (
    "paperId,title,abstract,authors,year,venue,citationCount,"
    "influentialCitationCount,isOpenAccess,openAccessPdf,url,references.paperId"
)

# References embedded in a /paper/search response aren't paginated by the API;
# cap how many we keep per paper so one heavily-cited result can't dominate
# the knowledge graph's edge count.
_MAX_REFERENCES_PER_PAPER = 50

_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.5


async def search(query: str, limit: int = 20) -> list[Paper]:
    settings = get_settings()
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    params = {"query": query, "limit": limit, "fields": FIELDS}
    async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
        data = await _get_with_retry(client, params, headers)

    papers: list[Paper] = []
    for item in data.get("data", []):
        if not item.get("title"):
            continue
        references = [
            f"s2:{ref['paperId']}"
            for ref in (item.get("references") or [])[:_MAX_REFERENCES_PER_PAPER]
            if ref.get("paperId")
        ]
        papers.append(
            Paper(
                paper_id=f"s2:{item['paperId']}",
                title=item["title"],
                abstract=item.get("abstract") or "",
                authors=[a.get("name", "") for a in item.get("authors", [])],
                year=item.get("year"),
                venue=item.get("venue") or None,
                citation_count=item.get("citationCount") or 0,
                influential_citation_count=item.get("influentialCitationCount") or 0,
                is_open_access=bool(item.get("isOpenAccess")),
                url=item.get("url"),
                source="semantic_scholar",
                references=references,
            )
        )
    return papers


async def _get_with_retry(client: httpx.AsyncClient, params: dict, headers: dict) -> dict:
    url = f"{get_settings().semantic_scholar_base_url}/paper/search"
    for attempt in range(_MAX_RETRIES):
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp.json()
        if attempt < _MAX_RETRIES - 1:
            retry_after = resp.headers.get("retry-after")
            delay = float(retry_after) if retry_after else _BASE_BACKOFF_S * (2**attempt)
            await asyncio.sleep(delay)
    resp.raise_for_status()  # exhausted retries; surface the 429 as an error
    return resp.json()
