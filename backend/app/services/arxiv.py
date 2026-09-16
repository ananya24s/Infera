"""Thin client for the arXiv Atom API."""
from __future__ import annotations

from xml.etree import ElementTree as ET

import httpx

from app.config import get_settings
from app.models.schemas import Paper

ATOM_NS = "{http://www.w3.org/2005/Atom}"


async def search(query: str, limit: int = 20) -> list[Paper]:
    settings = get_settings()
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
        resp = await client.get(settings.arxiv_base_url, params=params)
        resp.raise_for_status()
        xml_text = resp.text

    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        arxiv_id = (entry.findtext(f"{ATOM_NS}id") or "").rsplit("/", 1)[-1]
        title = (entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " ")
        summary = (entry.findtext(f"{ATOM_NS}summary") or "").strip().replace("\n", " ")
        published = entry.findtext(f"{ATOM_NS}published") or ""
        year = int(published[:4]) if published[:4].isdigit() else None
        authors = [
            (a.findtext(f"{ATOM_NS}name") or "").strip()
            for a in entry.findall(f"{ATOM_NS}author")
        ]
        if not title:
            continue
        papers.append(
            Paper(
                paper_id=f"arxiv:{arxiv_id}",
                title=title,
                abstract=summary,
                authors=authors,
                year=year,
                venue="arXiv",
                citation_count=0,
                influential_citation_count=0,
                is_open_access=True,
                url=f"https://arxiv.org/abs/{arxiv_id}",
                source="arxiv",
            )
        )
    return papers
