# -------------------------------------- #
# Repository root and standard data directories for CCAS packages.
# -------------------------------------- #
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ccas/paths.py -> parent is ccas/ -> repo root
REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Load `.env` from repository root (idempotent)."""
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()


def papers_output_dir() -> Path:
    """CSV/JSON artifacts from PDF extraction and paper metadata pipelines."""
    return REPO_ROOT / "ccas" / "papers" / "output"


def relevance_output_dir() -> Path:
    """Performance scores, trained relevance model, predictions."""
    return REPO_ROOT / "ccas" / "relevance" / "output"


def cities_data_dir() -> Path:
    """City deep-research inputs and SQLite/CSV outputs."""
    return REPO_ROOT / "ccas" / "cities" / "data"

