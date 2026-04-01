# -------------------------------------- #
# Fetch full-text PDF bytes for a paper using metadata from the `papers` table
# (or any compatible dict). Resolution order:
#   1. Explicit pdf / OA URL columns on the row
#   2. Semantic Scholar (DOI or corpus id) → openAccessPdf.url
#   3. Title search on Semantic Scholar → openAccessPdf.url
#   4. Optional Unpaywall (requires UNPAYWALL_EMAIL in env) for DOI
# -------------------------------------- #
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import quote

import requests

from ccas.paths import load_env, papers_output_dir
from ccas.relevance.fetch_abstracts import get_paper, search_paper, REQUEST_DELAY_S

load_env()

S2_PDF_FIELDS = "paperId,title,year,openAccessPdf,externalIds"
# Reasonable cap to avoid huge downloads / non-PDF HTML error pages
MAX_PDF_BYTES = 50 * 1024 * 1024
DEFAULT_UA = "CCAS/1.0 (academic PDF fetch; +https://github.com/)"

_UNPAYWALL = "https://api.unpaywall.org/v2"


def _get_str(row: Mapping[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _normalize_doi(doi: str) -> str:
    s = doi.strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    if s.lower().startswith("doi:"):
        s = s[4:].strip()
    return s


def _doi_to_s2_paper_id(doi: str) -> str:
    """Semantic Scholar accepts paper ids like DOI:10.1234/...."""
    return "DOI:" + _normalize_doi(doi)


def _is_pdf_magic(data: bytes) -> bool:
    return len(data) >= 5 and data[:5] == b"%PDF-"


def download_pdf_bytes(url: str, *, timeout_s: float = 120.0) -> bytes:
    """HTTP(S) GET; validates size and PDF magic bytes."""
    headers = {"User-Agent": os.environ.get("HTTP_USER_AGENT", DEFAULT_UA)}
    with requests.get(url, headers=headers, timeout=timeout_s, stream=True) as r:
        r.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in r.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_PDF_BYTES:
                raise PdfFetchError(
                    f"Download exceeded {MAX_PDF_BYTES} bytes; aborting (url={url[:80]}...)."
                )
            chunks.append(chunk)
    data = b"".join(chunks)
    if not _is_pdf_magic(data):
        raise PdfFetchError(
            "Response does not look like a PDF (missing %PDF- header). "
            f"The URL may point to an HTML landing page. url={url[:120]}..."
        )
    return data


def _open_access_url_from_s2_paper(paper: Mapping[str, Any]) -> Optional[str]:
    oa = paper.get("openAccessPdf")
    if not oa or not isinstance(oa, dict):
        return None
    url = oa.get("url")
    if isinstance(url, str) and url.strip().startswith("http"):
        return url.strip()
    return None


def _normalize_openalex_work_id(raw: str) -> Optional[str]:
    m = re.search(r"(W\d{8,})", raw.strip())
    return m.group(1) if m else None


def _openalex_pdf_url_from_row(row: Mapping[str, Any]) -> Optional[str]:
    """
    OpenAlex `works` often includes `best_oa_location.pdf_url` (matches your `openalex_id` column).
    See https://docs.openalex.org/api-entities/works
    """
    raw = _get_str(row, "openalex_id", "openalex_url")
    if not raw:
        return None
    wid = _normalize_openalex_work_id(raw)
    if not wid:
        return None
    mail = (
        os.environ.get("OPENALEX_CONTACT_EMAIL")
        or os.environ.get("UNPAYWALL_EMAIL")
        or "mailto:admin@localhost"
    )
    headers = {"User-Agent": f"CCAS/1.0 ({mail})"}
    try:
        r = requests.get(
            f"https://api.openalex.org/works/{wid}",
            timeout=25,
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None
    for loc_key in ("best_oa_location", "primary_location"):
        loc = data.get(loc_key) or {}
        u = loc.get("pdf_url")
        if isinstance(u, str) and u.startswith("http"):
            return u.strip()
    oa = data.get("open_access") or {}
    u = oa.get("oa_url")
    if isinstance(u, str) and u.startswith("http") and u.lower().rstrip().endswith(".pdf"):
        return u.strip()
    return None


def _unpaywall_pdf_url(doi: str) -> Optional[str]:
    email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if not email:
        return None
    d = _normalize_doi(doi)
    if not d:
        return None
    try:
        r = requests.get(
            f"{_UNPAYWALL}/{quote(doi, safe=':')}",
            params={"email": email},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None
    loc = data.get("best_oa_location") or {}
    for key in ("url_for_pdf", "url"):
        u = loc.get(key)
        if isinstance(u, str) and u.startswith("http"):
            return u
    return None


def resolve_pdf_url_from_metadata(row: Mapping[str, Any]) -> tuple[Optional[str], str]:
    """
    Find a downloadable PDF URL from a papers-table-like dict (no download).

    Returns (url_or_none, reason_label).
    """
    direct = _get_str(
        row,
        "pdf_url",
        "open_access_pdf_url",
        "oa_pdf_url",
        "pdf_link",
    )
    if direct:
        return direct, "column_pdf_url"

    oa_pdf = _openalex_pdf_url_from_row(row)
    if oa_pdf:
        return oa_pdf, "openalex_pdf_url"

    doi = _get_str(row, "doi", "DOI")
    s2_id = _get_str(
        row,
        "semantic_scholar_id",
        "s2_paper_id",
        "ss_corpus_id",
        "corpus_id",
    )

    if s2_id:
        time.sleep(REQUEST_DELAY_S)
        paper = get_paper(s2_id, fields=S2_PDF_FIELDS)
        if paper:
            u = _open_access_url_from_s2_paper(paper)
            if u:
                return u, "semantic_scholar_id_open_access"

    if doi:
        time.sleep(REQUEST_DELAY_S)
        paper = get_paper(_doi_to_s2_paper_id(doi), fields=S2_PDF_FIELDS)
        if paper:
            u = _open_access_url_from_s2_paper(paper)
            if u:
                return u, "semantic_scholar_doi_open_access"
        time.sleep(REQUEST_DELAY_S)
        u = _unpaywall_pdf_url(doi)
        if u:
            return u, "unpaywall"

    title = _get_str(row, "title")
    if title:
        hits = search_paper(title, limit=8)
        time.sleep(REQUEST_DELAY_S)
        for h in hits:
            pid = h.get("paperId")
            if not pid:
                continue
            paper = get_paper(pid, fields=S2_PDF_FIELDS)
            time.sleep(REQUEST_DELAY_S)
            if paper:
                u = _open_access_url_from_s2_paper(paper)
                if u:
                    return u, "semantic_scholar_title_search_open_access"

    return None, "not_found"


@dataclass
class PdfFetchResult:
    pdf_bytes: bytes
    source: str
    resolved_url: str
    supabase_paper_id: Optional[str] = None


class PdfFetchError(RuntimeError):
    """Raised when no PDF URL is found or download/validation fails."""


def fetch_pdf_bytes_from_row(row: Mapping[str, Any]) -> PdfFetchResult:
    """
    Resolve a PDF URL from row fields and download bytes.

    `row` should include any of: pdf_url / doi / semantic_scholar_id / title.
    """
    url, source = resolve_pdf_url_from_metadata(row)
    if not url:
        raise PdfFetchError(
            "Could not resolve an open-access PDF URL. "
            "Add pdf_url on the row, or a resolvable DOI / Semantic Scholar id / title."
        )
    try:
        data = download_pdf_bytes(url)
    except PdfFetchError:
        raise
    except Exception as e:
        raise PdfFetchError(f"Download failed: {e}") from e
    sid = _get_str(row, "id")
    return PdfFetchResult(
        pdf_bytes=data,
        source=source,
        resolved_url=url,
        supabase_paper_id=sid,
    )


def fetch_pdf_for_supabase_paper(
    paper_id: str,
    *,
    client: Any = None,
    columns: str = "*",
) -> PdfFetchResult:
    """
    Load one row from `public.papers` by primary key and fetch its PDF.

    Parameters
    ----------
    paper_id :
        UUID string of `papers.id`.
    client :
        Optional Supabase client; defaults to anon `get_supabase()`.
    columns :
        SELECT list; use '*' if your table has pdf_url, doi, title, etc.
    """
    from ccas.db.queries import fetch_paper_by_id

    row = fetch_paper_by_id(paper_id, client=client, columns=columns)
    if row is None:
        raise PdfFetchError(f"No paper found in Supabase for id={paper_id!r}")
    return fetch_pdf_bytes_from_row(row)


def save_pdf(result: PdfFetchResult, path: Path | str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(result.pdf_bytes)


def extract_text_from_pdf_bytes(pdf_bytes: bytes, *, max_chars: int | None = 8000) -> str:
    """
    Open PDF bytes with PyMuPDF and run the same cleaning as `pdf_func.pdf2text`.
    Truncate to `max_chars` (default 8000) for LLM prompts; pass max_chars=None for full text.
    """
    import fitz

    from ccas.papers.pdf_func import pdf2text

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        text = pdf2text(doc) or ""
    finally:
        doc.close()
    if max_chars is not None:
        text = text[:max_chars]
    return text


def fetch_pdf_text_for_supabase_paper(
    paper_id: str,
    *,
    client: Any = None,
    columns: str = "*",
    max_chars: int | None = 8000,
) -> tuple[str, PdfFetchResult]:
    """Download PDF for a DB row and return extracted text plus fetch metadata."""
    result = fetch_pdf_for_supabase_paper(paper_id, client=client, columns=columns)
    text = extract_text_from_pdf_bytes(result.pdf_bytes, max_chars=max_chars)
    return text, result


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Fetch PDF for a papers row (Supabase id) or print resolution only."
    )
    ap.add_argument("paper_id", nargs="?", help="Supabase papers.id (UUID)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print resolved URL and source, do not download",
    )
    ap.add_argument("--out", type=Path, help="Write PDF to this path")
    args = ap.parse_args()

    if not args.paper_id:
        ap.error("paper_id is required unless using --help")

    from ccas.db.queries import fetch_paper_by_id

    row = fetch_paper_by_id(args.paper_id, columns="*")
    if row is None:
        raise SystemExit(f"No paper found for id={args.paper_id!r}")

    url, source = resolve_pdf_url_from_metadata(row)
    print("resolved_url:", url)
    print("source:", source)
    if args.dry_run:
        return
    if not url:
        raise SystemExit("No PDF URL resolved.")

    result = fetch_pdf_bytes_from_row(row)
    out = args.out
    if not out:
        safe = re.sub(r"[^\w\-]+", "_", str(row.get("title") or "paper"))[:80]
        out = papers_output_dir() / "pdfs" / f"{args.paper_id}_{safe}.pdf"
    save_pdf(result, out)
    print("Wrote", out, f"({len(result.pdf_bytes)} bytes)")


if __name__ == "__main__":
    main()
