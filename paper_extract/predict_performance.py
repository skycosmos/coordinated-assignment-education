#!/usr/bin/env python3
"""
Predict performance score for papers from title + abstract using the saved model.

Usage:
  python predict_performance.py                          # predict on paper_to_abstract.csv
  python predict_performance.py --title "..." --abstract "..."  # single prediction
"""

import argparse
import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os

DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DIR / "output"
MODEL_DIR = OUTPUT_DIR / "performance_model"
EMBEDDING_MODEL = "text-embedding-3-small"

load_dotenv(DIR / ".env")
load_dotenv()


def load_model():
    """Load saved pipeline and metadata."""
    with open(MODEL_DIR / "pipeline.pkl", "rb") as f:
        pipe = pickle.load(f)
    with open(MODEL_DIR / "metadata.json") as f:
        meta = json.load(f)
    return pipe, meta


def embed_texts(client: OpenAI, texts: list[str]) -> np.ndarray:
    """Embed texts; return (n, dim) array."""
    out = []
    for i in range(0, len(texts), 100):
        batch = [t[:8000] for t in texts[i : i + 100]]
        r = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        out.extend([e.embedding for e in r.data])
    return np.array(out)


def predict_batch(df: pd.DataFrame, pipe, client: OpenAI) -> np.ndarray:
    """Predict performance score for a dataframe with columns title, abstract."""
    texts = ("title: " + df["title"].astype(str).fillna("") + "\nabstract: " + df["abstract"].astype(str).fillna("")).tolist()
    X = embed_texts(client, texts)
    return pipe.predict(X)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="", help="Paper title (for single prediction)")
    ap.add_argument("--abstract", default="", help="Paper abstract (for single prediction)")
    ap.add_argument("--input", default=None, help="CSV with paper_name, title, abstract (default: output/paper_to_abstract.csv)")
    ap.add_argument("--output", default=None, help="Output CSV with predictions")
    args = ap.parse_args()

    pipe, meta = load_model()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY not set")

    if args.title or args.abstract:
        text = "title: " + (args.title or "") + "\nabstract: " + (args.abstract or "")
        X = embed_texts(client, [text])
        score = float(pipe.predict(X)[0])
        print("Predicted performance score:", round(score, 4))
        return

    input_path = Path(args.input) if args.input else OUTPUT_DIR / "paper_to_abstract.csv"
    df = pd.read_csv(input_path)
    if "title" not in df.columns:
        df["title"] = ""
    if "abstract" not in df.columns:
        df["abstract"] = ""
    pred = predict_batch(df, pipe, client)
    df["predicted_performance_score"] = np.round(pred, 4)
    out_path = Path(args.output) if args.output else OUTPUT_DIR / "paper_predicted_scores.csv"
    df.to_csv(out_path, index=False)
    print("Predictions saved to", out_path)
    print("Score stats: min={:.2f} max={:.2f} mean={:.2f}".format(pred.min(), pred.max(), pred.mean()))


if __name__ == "__main__":
    main()
