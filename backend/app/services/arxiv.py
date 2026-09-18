"""Thin client for the arXiv Atom API.

Uses `requests` rather than httpx: arxiv.org's edge intermittently returns
406 to httpx's TLS/handshake fingerprint specifically (reproduced with
identical headers and both HTTP/1.1 and HTTP/2 — httpx still gets blocked
while `requests` and plain `curl` are consistently accepted), so httpx isn't
usable here.
"""
from __future__ import annotations

import asyncio
from xml.etree import ElementTree as ET

import requests

from app.config import get_settings
from app.models.schemas import Paper

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _fetch(url: str, params: dict, timeout: float) -> str:
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.text


async def search(query: str, limit: int = 20) -> list[Paper]:
    settings = get_settings()
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    xml_text = await asyncio.to_thread(
        _fetch, settings.arxiv_base_url, params, settings.request_timeout_s
    )

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
