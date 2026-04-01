#!/usr/bin/env python3
"""
Run the full performance evaluation and ML pipeline:

  1. Compute ground-truth performance scores (city-level=1.0, country-level=0.3)
  2. Fetch abstracts via Semantic Scholar API (free)
  3. Train predictor: text-embedding-3-small + Ridge regression

Usage:
  python run_performance_pipeline.py              # full run
  python run_performance_pipeline.py --skip-fetch  # use existing paper_to_abstract.csv
  python run_performance_pipeline.py --max-papers 10   # test on 10 papers
"""

import argparse

from ccas.relevance.performance_eval import run_evaluation
from ccas.relevance.fetch_abstracts import run_fetch
from ccas.relevance.train_performance_predictor import load_data, train_and_save


def main():
    ap = argparse.ArgumentParser(description="Run performance eval + abstract fetch + train predictor")
    ap.add_argument("--skip-fetch", action="store_true", help="Skip abstract fetch; use existing paper_to_abstract.csv")
    ap.add_argument("--max-papers", type=int, default=None, help="Limit number of papers (for testing)")
    args = ap.parse_args()

    print("Step 1: Computing performance scores from CCAS data...")
    run_evaluation()
    print()

    if not args.skip_fetch:
        print("Step 2: Fetching abstracts (Semantic Scholar, free)...")
        run_fetch(max_papers=args.max_papers)
        print()
    else:
        print("Step 2: Skipping abstract fetch (--skip-fetch).")
        print()

    print("Step 3: Training ML predictor (embeddings + Ridge)...")
    df, _ = load_data()
    if args.max_papers:
        df = df.head(args.max_papers)
    train_and_save(df)
    print("\nDone. Use predict_performance.py to predict on new papers.")


if __name__ == "__main__":
    main()
