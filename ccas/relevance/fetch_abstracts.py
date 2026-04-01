#!/usr/bin/env python3
from __future__ import annotations

"""
Retrieve paper abstracts via Semantic Scholar API (free, no API key required).

Uses paper title (and optionally first author) to search and fetch abstract.
Saves results to output/paper_to_metadata.csv (adds/updates abstract column).
"""

import os
import time
import re
import pandas as pd
import requests
from pathlib import Path
from urllib.parse import quote

from ccas.paths import papers_output_dir, relevance_output_dir

PAPERS_OUT = papers_output_dir()
REL_OUT = relevance_output_dir()
BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Rate limit: 100 requests per 5 min without key; use 1.5s delay to be safe
REQUEST_DELAY_S = 1.5


def _s2_headers() -> dict[str, str]:
    """Optional SEMANTIC_SCHOLAR_API_KEY in .env avoids 429 rate limits."""
    h: dict[str, str] = {}
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if key:
        h["x-api-key"] = key
    return h


def search_paper(title: str, limit: int = 1) -> list[dict]:
    """Search Semantic Scholar by title; return list of hits."""
    url = f"{BASE_URL}/paper/search"
    params = {"query": title[:200], "limit": limit, "fields": "paperId,title,year"}
    try:
        r = requests.get(url, params=params, timeout=15, headers=_s2_headers())
        r.raise_for_status()
        data = r.json()
        return data.get("data") or []
    except Exception:
        return []


def get_paper(paper_id: str, fields: str = "title,abstract,year") -> dict | None:
    """Fetch paper by ID with given fields. Encodes DOIs and other ids for the path segment."""
    enc = quote(paper_id, safe="")
    url = f"{BASE_URL}/paper/{enc}"
    params = {"fields": fields}
    try:
        r = requests.get(url, params=params, timeout=15, headers=_s2_headers())
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def normalize_title(t: str) -> str:
    """Light normalization for matching."""
    if not isinstance(t, str):
        return ""
    t = re.sub(r"\s+", " ", t).strip()
    return t.lower()[:200]


def fetch_abstract_for_title(title: str, first_author: str | None = None) -> str | None:
    """
    Search by title, pick best match, return abstract.
    Optional first_author used to disambiguate when multiple hits.
    """
    hits = search_paper(title, limit=3)
    time.sleep(REQUEST_DELAY_S)
    if not hits:
        return None
    # Prefer exact title match
    title_norm = normalize_title(title)
    for h in hits:
        if normalize_title(h.get("title") or "") == title_norm:
            pid = h.get("paperId")
            if pid:
                paper = get_paper(pid)
                time.sleep(REQUEST_DELAY_S)
                if paper:
                    return (paper.get("abstract") or "").strip() or None
            break
    # Else take first hit
    pid = hits[0].get("paperId")
    if not pid:
        return None
    paper = get_paper(pid)
    time.sleep(REQUEST_DELAY_S)
    if paper:
        return (paper.get("abstract") or "").strip() or None
    return None


def run_fetch(
    metadata_path: Path | None = None,
    output_path: Path | None = None,
    max_papers: int | None = None,
) -> pd.DataFrame:
    """
    Load paper_to_metadata.csv, fetch abstract per paper, add/update abstract column, save back.
    """
    metadata_path = metadata_path or (PAPERS_OUT / "paper_to_metadata.csv")
    output_path = output_path or metadata_path
    df = pd.read_csv(metadata_path)
    if max_papers is not None:
        df = df.head(max_papers).copy()
    else:
        df = df.copy()
    if "abstract" not in df.columns:
        df["abstract"] = ""
    for i, r in df.iterrows():
        title = r.get("title") or ""
        authors = r.get("authors") or ""
        first_author = None
        if isinstance(authors, str) and "," in authors:
            first_author = authors.split(",")[0].strip()
        abstract = fetch_abstract_for_title(title, first_author)
        df.at[i, "abstract"] = abstract or ""
        print(f"[{i+1}/{len(df)}] {r['paper_name'][:40]:40} -> {'OK' if abstract else 'missing'}")
    df.to_csv(output_path, index=False)
    REL_OUT.mkdir(parents=True, exist_ok=True)
    export = df.copy()
    for col in ("paper_name", "title", "abstract"):
        if col not in export.columns:
            export[col] = ""
    export[["paper_name", "title", "abstract"]].to_csv(REL_OUT / "paper_to_abstract.csv", index=False)
    return df


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None  # e.g. 5 for testing
    run_fetch(max_papers=n)
