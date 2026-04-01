#!/usr/bin/env python3
"""
Performance evaluation system for CCAS paper relevance.

Quantifies the value of policy information provided by each paper:
- City-level policy information = most valuable (weight 1.0)
- Country-level policy information = somewhat useful (weight 0.3)
- No / N/A systems = 0

Output: per-paper performance score and optional normalized (0-1) score.
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path

from ccas.paths import papers_output_dir, relevance_output_dir

# Weights for information value (tunable)
WEIGHT_CITY = 1.0
WEIGHT_COUNTRY = 0.3

PAPERS_OUT = papers_output_dir()
REL_OUT = relevance_output_dir()


def load_ccas_systems(path: Path | None = None) -> pd.DataFrame:
    """Load CCAS systems table (cleaned)."""
    path = path or (PAPERS_OUT / "paper_to_ccas_systems_cleaned.csv")
    return pd.read_csv(path)


def compute_paper_scores(
    df_ccas: pd.DataFrame,
    weight_city: float = WEIGHT_CITY,
    weight_country: float = WEIGHT_COUNTRY,
) -> pd.DataFrame:
    """
    Compute performance score per paper from CCAS systems.

    - Rows with non-null city_id (and city_name) count as city-level → weight_city.
    - Rows with null city_id but non-null country code count as country-level → weight_country.
    - Rows with neither (N/A, no system) contribute 0.

    Each (paper, city_id or paper, country) is counted once per paper (we count
    distinct systems: city-level systems vs country-only systems).
    """
    records = []
    for paper_name, grp in df_ccas.groupby("paper_name"):
        city_systems = set()
        country_systems = set()
        for _, row in grp.iterrows():
            cid = row.get("city_id") or row.get("city_name")
            country = row.get("city_country_code")
            def ok(s):
                if pd.isna(s): return False
                t = str(s).strip()
                return t and t.lower() != "nan" and t.upper() != "N/A"
            if ok(cid):
                city_systems.add((paper_name, cid))
            elif ok(country):
                country_systems.add((paper_name, country))
        n_city = len(city_systems)
        n_country = len(country_systems)
        score_raw = weight_city * n_city + weight_country * n_country
        records.append({
            "paper_name": paper_name,
            "n_city_level": n_city,
            "n_country_level": n_country,
            "performance_score": round(score_raw, 4),
        })
    return pd.DataFrame(records)


def normalize_scores(df: pd.DataFrame, col: str = "performance_score") -> pd.DataFrame:
    """Add normalized score in [0, 1] (min-max)."""
    df = df.copy()
    s = df[col]
    lo, hi = s.min(), s.max()
    if hi > lo:
        df["performance_score_norm"] = ((s - lo) / (hi - lo)).round(4)
    else:
        df["performance_score_norm"] = 0.0 if hi == 0 else 1.0
    return df


def run_evaluation(
    output_path: Path | None = None,
    weight_city: float = WEIGHT_CITY,
    weight_country: float = WEIGHT_COUNTRY,
) -> pd.DataFrame:
    """
    Load CCAS data, compute scores, optionally save, return score table.
    """
    df_ccas = load_ccas_systems()
    df_scores = compute_paper_scores(df_ccas, weight_city=weight_city, weight_country=weight_country)
    df_scores = normalize_scores(df_scores)
    output_path = output_path or (REL_OUT / "paper_performance_scores.csv")
    REL_OUT.mkdir(parents=True, exist_ok=True)
    df_scores.to_csv(output_path, index=False)
    return df_scores


if __name__ == "__main__":
    df = run_evaluation()
    print("Performance score summary:")
    print(df.describe())
    print("\nTop 5 by performance_score:")
    print(df.nlargest(5, "performance_score")[["paper_name", "n_city_level", "n_country_level", "performance_score", "performance_score_norm"]])
