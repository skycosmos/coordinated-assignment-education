## CCAS (Coordinated Choice and Assignment Systems)

This repository gathers and processes data on school choice and assignment systems worldwide: city-level deep research, PDF-based paper extraction with an LLM, and a **supervised** model that predicts how much policy-relevant signal a paper is likely to yield (so you can prioritize which papers to run through expensive extraction).

### Layout

| Path | Role |
|------|------|
| `ccas/db/` | Supabase clients (`get_supabase`, …) and `queries` for papers / researchers / RL edge API |
| `ccas/cities/` | OpenAI deep-research jobs per city; SQLite + CSV under `ccas/cities/data/` |
| `ccas/papers/` | Dropbox PDF download, text extraction, combined LLM extraction; CSV outputs under `ccas/papers/output/` |
| `ccas/relevance/` | Performance scores from CCAS tables, Semantic Scholar abstracts, **embedding + Ridge** training; artifacts under `ccas/relevance/output/` |
| `sql/` | Reference SQL (e.g. `rl_schema.sql` for Supabase) |

Legacy import paths at the repo root (`supabase_client.py`, `rl_api_client.py`, `supabase_queries.py`) re-export the `ccas.db` modules for older scripts.

### Setup

1. Create a `.env` file at the **repository root** with at least `OPENAI_API_KEY=...` and, if you use Supabase, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, etc.

2. Install the package in editable mode (recommended):

```bash
cd /path/to/ccas
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
```

Dependencies are listed in `pyproject.toml`; `requirements.txt` remains for quick `pip install -r` installs without the package.

### City deep research (SQLite)

```bash
python -m ccas.cities.run_city_research
```

Uses `ccas/cities/data/output/ccas_city.db` and inputs under `ccas/cities/data/input/`.

### Paper extraction (Dropbox + LLM)

```bash
python -m ccas.papers.main_paper_extract
```

Expects `ccas/papers/output/paper_list.csv` and writes CSV/JSON next to it.

### Fetch a PDF from `papers` (for LLM extraction)

`ccas/papers/academic_pdf.py` resolves an open-access PDF URL from row fields, downloads bytes, and can extract text for your existing LLM pipeline.

**Resolution order:** `pdf_url` / `open_access_pdf_url` (or similar) → Semantic Scholar (`semantic_scholar_id` or `DOI:` lookup, or title search) → optional **Unpaywall** if `UNPAYWALL_EMAIL` is set in `.env`.

**Semantic Scholar:** requests use optional `SEMANTIC_SCHOLAR_API_KEY` (see [S2 API](https://www.semanticscholar.org/product/api)) to reduce `429` rate limits. Paper IDs in URLs are **URL-encoded** (fixes DOIs containing `/`).

**In code:**

```python
from ccas.papers.academic_pdf import (
    fetch_pdf_text_for_supabase_paper,
    fetch_pdf_for_supabase_paper,
    extract_text_from_pdf_bytes,
)
from ccas.papers.openai_func import read_paper
from openai import OpenAI

text, result = fetch_pdf_text_for_supabase_paper("<papers.id uuid>")
# result.resolved_url, result.source — how the PDF was found
client = OpenAI()
out = read_paper(client, text, model="gpt-4o", temp=0.2)
```

**CLI:**

```bash
python -m ccas.papers.academic_pdf <papers-uuid> --dry-run   # show URL + source only
python -m ccas.papers.academic_pdf <papers-uuid> --out /tmp/paper.pdf
```

`ccas/db/queries.py` adds `fetch_paper_by_id` for loading a single row.

### Supervised relevance / performance model

Ground-truth scores come from city- vs country-level CCAS rows (`performance_eval`). Training uses **OpenAI embeddings** (`text-embedding-3-small`) and **sklearn Ridge** regression on title + abstract.

**Full pipeline** (scores → fetch abstracts → train):

```bash
python -m ccas.relevance.run_performance_pipeline
```

**Train only** (requires `ccas/relevance/output/paper_performance_scores.csv` and merged title/abstract data):

```bash
python -m ccas.relevance.train_performance_predictor
```

**Predict** on metadata or a CSV with `title` and `abstract`:

```bash
python -m ccas.relevance.predict_performance
python -m ccas.relevance.predict_performance --title "..." --abstract "..."
```

Use a valid `OPENAI_API_KEY` for embedding calls.

### Tuning relevance weights

Edit `WEIGHT_CITY` and `WEIGHT_COUNTRY` in `ccas/relevance/performance_eval.py`, then re-run evaluation and training.
