# Performance Evaluation & ML Predictor for CCAS Papers

## Overview

1. **Performance evaluation**: Quantifies how much policy-relevant information each paper provides.
   - **City-level** policy information = most valuable → weight **1.0**
   - **Country-level** policy information = somewhat useful → weight **0.3**
   - Score = (number of distinct city-level systems × 1.0) + (number of distinct country-level systems × 0.3)

2. **Abstract retrieval**: Fetches abstracts via **Semantic Scholar API** (free, no API key).

3. **ML predictor**: Predicts performance score from **title + abstract** using:
   - **OpenAI text-embedding-3-small** (embeddings only, no chat)
   - **sklearn Ridge regression** on embeddings → score

## Cost estimate (OpenAI only)

| Component | Model | Approx. usage | Price (approx.) |
|-----------|--------|----------------|-----------------|
| Embeddings | text-embedding-3-small | ~220 papers × ~200 tokens ≈ 44k tokens | **~$0.001** |
| Chat/completion | Not used | 0 | $0 |
| **Total** | | | **&lt; $0.01** |

- **Abstracts**: Semantic Scholar is free (no key required; rate limit ~100 req/5 min).
- **Training**: No GPT calls; only embeddings. Inference uses the same embedding API (~same per 1k tokens).

If you later add **gpt-4o-mini** for labeling or augmentation: input ~$0.15/1M tokens, output ~$0.60/1M; 220 papers × 500 input + 50 output ≈ **~$0.02** extra per full run.

## Quick start

```bash
cd paper_extract
# Optional: create .env with OPENAI_API_KEY=...
pip install -r ../requirements.txt

# Full pipeline (scores + fetch abstracts + train)
python run_performance_pipeline.py

# Skip abstract fetch if you already have paper_to_abstract.csv
python run_performance_pipeline.py --skip-fetch

# Test on 10 papers only
python run_performance_pipeline.py --max-papers 10
```

## Step-by-step

```bash
# 1. Compute ground-truth scores (no API)
python -c "from performance_eval import run_evaluation; run_evaluation()"

# 2. Fetch abstracts (free API; ~1.5 s per paper)
python fetch_abstracts.py          # all papers
python fetch_abstracts.py 5        # first 5 papers

# 3. Train predictor (uses OpenAI embeddings; ~$0.001)
python train_performance_predictor.py

# 4. Predict on new papers
python predict_performance.py --input output/paper_to_abstract.csv --output output/paper_predicted_scores.csv
python predict_performance.py --title "School choice in Boston" --abstract "We study..."
```

## Outputs

| File | Description |
|------|-------------|
| `output/paper_performance_scores.csv` | Ground-truth: paper_name, n_city_level, n_country_level, performance_score, performance_score_norm |
| `output/paper_to_abstract.csv` | paper_name, title, abstract (from Semantic Scholar) |
| `output/performance_model/pipeline.pkl` | Trained Ridge pipeline (StandardScaler + Ridge) |
| `output/performance_model/metadata.json` | Token usage, cost, test R², CV R² |
| `output/paper_predicted_scores.csv` | Predictions from predict_performance.py |

## Tuning

- **Weights**: Edit `performance_eval.WEIGHT_CITY` and `WEIGHT_COUNTRY` (default 1.0 and 0.3).
- **Model**: In `train_performance_predictor.py` you can switch to `GradientBoostingRegressor` for more flexibility (may overfit on small n).
