# CCAS
Review of centralized admission and student assignment systems worldwide.

## Project purpose
This repository gathers and processes data on Coordinated Choice and Assignment Systems (CCAS) for cities worldwide. The code in `deep_research` submits background research jobs to an OpenAI Responses model, polls for JSON outputs, and stores structured CCAS metadata in a SQLite database.

## Key files
- `deep_research/main.py`: main runner — submits background jobs, polls results, and updates the `ccas_city` table in `ccas_city.db`.
- `deep_research/prompt_gen.py`: builds the JSON-only prompt used by the model.
- `deep_research/country_cities.csv`: list of target cities.
- `deep_research/db_process.sql`: sqlite3 script to export `ccas_city` table to CSV.
- `deep_research/requirements.txt`: Python dependencies.
- `paper/`: helper utilities for PDF processing and OpenAI functions used for analysis.

## Quick setup
1. Create a `.env` file (one level up from `deep_research`) containing `OPENAI_API_KEY=your_key_here`.
2. Install dependencies:

```bash
pip install -r deep_research/requirements.txt
```

3. Ensure a SQLite database `ccas_city.db` is present in `deep_research` and contains a `ccas_city` table with rows to process. Rows with empty `ccas_status` will be processed.

## Run
From the repository root:

```bash
cd deep_research
python main.py
```

The script prints submission and polling logs and updates the `ccas_city` table with the model's JSON fields.

## Export results
Use the included SQLite export script to create a CSV of the results:

```bash
cd deep_research
sqlite3 ccas_city.db < db_process.sql
```

## Configuration & tuning
- Adjust `MAX_RETRIES`, `POLL_INTERVAL`, and `JOB_TIMEOUT_MINUTES` in `deep_research/main.py` as needed.
- Modify `deep_research/prompt_gen.py` to change research scope, fields, or output schema.

## Notes
- `main.py` expects the OpenAI Responses client to be configured via `OPENAI_API_KEY` in the environment.
- Back up `ccas_city.db` before testing or bulk runs.

If you want, I can populate `ccas_city.db`, run a test, or add a short CONTRIBUTING section.
