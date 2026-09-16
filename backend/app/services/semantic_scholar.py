"""Thin client for the Semantic Scholar Graph API (no key required for light use)."""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.models.schemas import Paper

FIELDS = (
    "paperId,title,abstract,authors,year,venue,citationCount,"
    "influentialCitationCount,isOpenAccess,openAccessPdf,url"
)


async def search(query: str, limit: int = 20) -> list[Paper]:
    settings = get_settings()
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    params = {"query": query, "limit": limit, "fields": FIELDS}
    async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
        resp = await client.get(
            f"{settings.semantic_scholar_base_url}/paper/search",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    papers: list[Paper] = []
    for item in data.get("data", []):
        if not item.get("title"):
            continue
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
            )
        )
    return papers
