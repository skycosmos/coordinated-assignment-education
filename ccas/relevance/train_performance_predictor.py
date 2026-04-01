#!/usr/bin/env python3
"""
Train a small ML model to predict paper performance score from title + abstract.

- Uses OpenAI text-embedding-3-small for embeddings (cheapest option; no chat/completion).
- Trains sklearn Ridge regression (or optional GradientBoosting) on embeddings -> score.
- Saves model and reports token usage + estimated cost.

Cost: ~$0.00002 per 1k tokens (embedding only). For ~220 papers × ~200 tokens ≈ $0.001.
"""

import os
import json
import pickle
import pandas as pd
import numpy as np
from openai import OpenAI

from ccas.paths import load_env, papers_output_dir, relevance_output_dir

# Prefer Ridge for small data; stable and no extra deps beyond sklearn
try:
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import cross_val_score, KFold
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except ImportError:
    Ridge = None

REL_OUT = relevance_output_dir()
PAPERS_OUT = papers_output_dir()
MODEL_DIR = REL_OUT / "performance_model"
EMBEDDING_MODEL = "text-embedding-3-small"
# Price per 1k tokens (embedding) — as of 2025
PRICE_PER_1K_TOKENS = 0.00002

load_env()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load performance scores and abstracts (merge with metadata for title if needed)."""
    scores_path = REL_OUT / "paper_performance_scores.csv"
    abstract_path = REL_OUT / "paper_to_abstract.csv"
    meta_path = PAPERS_OUT / "paper_to_metadata.csv"
    if not scores_path.exists():
        raise FileNotFoundError("Run performance_eval.run_evaluation() first to create paper_performance_scores.csv")
    df_scores = pd.read_csv(scores_path)
    if abstract_path.exists():
        df_abs = pd.read_csv(abstract_path)
    else:
        df_abs = pd.read_csv(meta_path)[["paper_name", "title"]].copy()
        df_abs["abstract"] = ""
    df = df_scores.merge(df_abs, on="paper_name", how="left")
    if "title" not in df.columns and meta_path.exists():
        meta = pd.read_csv(meta_path)[["paper_name", "title"]]
        df = df.merge(meta, on="paper_name", how="left")
    df["title"] = df.get("title", pd.Series([""] * len(df))).fillna("")
    df["abstract"] = df.get("abstract", pd.Series([""] * len(df))).fillna("")
    return df, df_scores


def embed_texts(client: OpenAI, texts: list[str], model: str = EMBEDDING_MODEL) -> tuple[np.ndarray, int]:
    """
    Embed a list of texts with OpenAI. Returns (array of shape (n, dim), total_tokens).
    """
    total_tokens = 0
    embeddings = []
    # API allows up to 2048 inputs per request; we batch to avoid token limit
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = [t[:8000] for t in texts[i : i + batch_size]]  # truncate long texts
        r = client.embeddings.create(model=model, input=batch)
        total_tokens += r.usage.total_tokens
        embeddings.extend([e.embedding for e in r.data])
    return np.array(embeddings), total_tokens


def train_and_save(
    df: pd.DataFrame,
    target_col: str = "performance_score",
    text_cols: tuple[str, str] = ("title", "abstract"),
    model_name: str = "ridge",
    test_frac: float = 0.2,
    random_state: int = 42,
) -> dict:
    """
    Build feature string from title+abstract, embed, train Ridge, save model and metadata.
    Returns dict with metrics and cost_estimate_usd.
    """
    if Ridge is None:
        raise ImportError("sklearn is required. Install with: pip install scikit-learn")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY not set")

    title_col, abstract_col = text_cols
    df = df.copy()
    df["_text"] = (
        "title: " + df[title_col].astype(str).fillna("") + "\nabstract: " + df[abstract_col].astype(str).fillna("")
    )
    texts = df["_text"].tolist()
    y = df[target_col].values

    print("Embedding texts with", EMBEDDING_MODEL, "...")
    X, total_tokens = embed_texts(client, texts)
    cost_estimate_usd = (total_tokens / 1000) * PRICE_PER_1K_TOKENS
    print(f"  Total tokens: {total_tokens} -> estimated cost ${cost_estimate_usd:.4f}")

    # Train/val split
    n = len(y)
    np.random.seed(random_state)
    idx = np.random.permutation(n)
    n_test = max(1, int(n * test_frac))
    test_idx, train_idx = idx[:n_test], idx[n_test:]
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    pipe = Pipeline([
        ("scale", StandardScaler()),
        ("ridge", Ridge(alpha=1.0)),
    ])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    cv = cross_val_score(pipe, X, y, cv=min(5, n // 2), scoring="r2")
    cv_r2_mean, cv_r2_std = float(cv.mean()), float(cv.std())

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_DIR / "pipeline.pkl", "wb") as f:
        pickle.dump(pipe, f)
    meta = {
        "embedding_model": EMBEDDING_MODEL,
        "total_tokens_used": total_tokens,
        "estimated_cost_usd": round(cost_estimate_usd, 4),
        "target": target_col,
        "test_metrics": {"mse": mse, "mae": mae, "r2": r2},
        "cv_r2_mean": cv_r2_mean,
        "cv_r2_std": cv_r2_std,
        "n_train": len(train_idx),
        "n_test": len(test_idx),
    }
    with open(MODEL_DIR / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("Metrics (test set):", meta["test_metrics"])
    print("CV R²:", f"{cv_r2_mean:.3f} ± {cv_r2_std:.3f}")
    print("Model saved to", MODEL_DIR)
    return meta


def main():
    df, _ = load_data()
    print(f"Loaded {len(df)} papers. Papers with abstract: {(df['abstract'].str.len() > 0).sum()}")
    meta = train_and_save(df)
    print("\nEstimated embedding cost: $", meta["estimated_cost_usd"])


if __name__ == "__main__":
    main()
