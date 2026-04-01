# Deprecated: import from `ccas.db.queries` instead.
from ccas.db.queries import (
    fetch_papers_sample,
    fetch_paper_by_id,
    fetch_paper_systems_for_city,
    fetch_visible_researchers,
    update_paper_keyword_score,
    update_paper_keyword_score_via_rl,
    insert_rl_run,
    insert_rl_outputs,
)

__all__ = [
    "fetch_papers_sample",
    "fetch_paper_by_id",
    "fetch_paper_systems_for_city",
    "fetch_visible_researchers",
    "update_paper_keyword_score",
    "update_paper_keyword_score_via_rl",
    "insert_rl_run",
    "insert_rl_outputs",
]
