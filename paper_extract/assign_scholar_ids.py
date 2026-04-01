#!/usr/bin/env python3
"""
Assign a unique Google Scholar ID to each paper using the scholarly package.

Uses paper_to_metadata.csv (paper_name, title, year, authors). For each paper,
searches Google Scholar by title, optionally disambiguates by year, and extracts
the Scholar "cites" ID from the first/best match. This ID is stable and can be
used as a unique paper identifier (e.g. in URLs like
https://scholar.google.com/scholar?cites=ID).

Output: paper_to_metadata.csv with an added scholar_id column, and/or
        output/paper_to_scholar_id.csv (paper_name, scholar_id, matched_title, matched_year).

Usage:
  pip install scholarly
  python assign_scholar_ids.py [--metadata-csv path] [--output-csv path] [--limit N] [--delay SEC]
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd

# Optional: scholarly can rate-limit; delay between requests (seconds)
DEFAULT_DELAY = 2.0


def extract_scholar_id_from_publication(pub: dict) -> str | None:
    """Extract the unique Scholar ID from a publication object from scholarly."""
    url = pub.get("citedby_url") or ""
    match = re.search(r"cites=(\d+)", url)
    return match.group(1) if match else None


def search_scholar_id(title: str, year: str | None, delay: float) -> tuple[str | None, str | None, str | None]:
    """
    Search Google Scholar by title and return (scholar_id, matched_title, matched_year).

    Uses scholarly.search_pubs(title). If year is provided and not "Unknown",
    prefers the first result with matching year; otherwise returns the first result.
    """
    try:
        from scholarly import scholarly
    except ImportError:
        raise ImportError("Install scholarly: pip install scholarly") from None

    search_query = scholarly.search_pubs(title)
    best_id = None
    best_title = None
    best_year = None
    year_str = str(year).strip() if year and str(year).strip() not in ("", "Unknown", "N/A") else None

    for pub in search_query:
        sid = extract_scholar_id_from_publication(pub)
        if not sid:
            continue
        bib = pub.get("bib") or {}
        pt = bib.get("title") or ""
        py = bib.get("pub_year") or ""
        if year_str and py and str(py).strip() == year_str:
            return sid, pt or None, py or None
        if best_id is None:
            best_id, best_title, best_year = sid, pt or None, py or None
        time.sleep(delay)

    return best_id, best_title, best_year


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign Google Scholar IDs to papers from metadata.")
    parser.add_argument(
        "--metadata-csv",
        default="output/paper_to_metadata.csv",
        help="Input CSV with columns paper_name, title, year, authors",
    )
    parser.add_argument(
        "--output-csv",
        default="output/paper_to_scholar_id.csv",
        help="Output CSV: paper_name, scholar_id, matched_title, matched_year",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Also add scholar_id to the metadata CSV (in place or to --merged-output)",
    )
    parser.add_argument(
        "--merged-output",
        default=None,
        help="If --merge, write merged metadata here (default: overwrite --metadata-csv)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only first N papers (for testing)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Seconds between Scholar requests")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    meta_path = base / args.metadata_csv
    out_path = base / args.output_csv

    if not meta_path.exists():
        raise SystemExit(f"Metadata CSV not found: {meta_path}")

    df = pd.read_csv(meta_path)
    for col in ("paper_name", "title"):
        if col not in df.columns:
            raise SystemExit(f"Missing column in {meta_path}: {col}")

    rows = df[["paper_name", "title"]].copy()
    if "year" in df.columns:
        rows["year"] = df["year"]
    else:
        rows["year"] = None

    if args.limit:
        rows = rows.head(args.limit)

    results = []
    for idx, row in rows.iterrows():
        paper_name = row["paper_name"]
        title = row["title"]
        year = row.get("year")
        print(f"Querying Scholar: {paper_name} -> {title!r} ({year})")
        try:
            sid, matched_title, matched_year = search_scholar_id(str(title), str(year) if year else None, args.delay)
            results.append({
                "paper_name": paper_name,
                "scholar_id": sid or "",
                "matched_title": matched_title or "",
                "matched_year": matched_year or "",
            })
            print(f"  -> scholar_id={sid or 'NOT FOUND'}")
        except Exception as e:
            print(f"  -> Error: {e}")
            results.append({
                "paper_name": paper_name,
                "scholar_id": "",
                "matched_title": "",
                "matched_year": "",
            })
        time.sleep(args.delay)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(out_path, index=False)
    print(f"Wrote {out_path}")

    if args.merge:
        id_map = {r["paper_name"]: r["scholar_id"] for r in results}
        df = pd.read_csv(meta_path)
        df["scholar_id"] = df["paper_name"].map(id_map)
        merge_path = Path(args.merged_output) if args.merged_output else meta_path
        merge_path = base / merge_path if not Path(args.merged_output).is_absolute() else Path(args.merged_output)
        df.to_csv(merge_path, index=False)
        print(f"Wrote merged metadata to {merge_path}")


if __name__ == "__main__":
    main()
