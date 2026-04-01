# -------------------------------------- #
# Project:          CCAS
# Reads: Supabase anon client (RLS-safe SELECT).
# Writes to papers / paper_systems / researchers: RL edge API (rl_api_client).
# Writes to rl_runs / rl_outputs: service role (get_supabase_admin), optional.
# -------------------------------------- #

from __future__ import annotations

from typing import Any, Mapping, Optional

from supabase import Client

from rl_api_client import rl_insert, rl_select, rl_update
from supabase_client import get_supabase, get_supabase_admin


def fetch_papers_sample(
    client: Optional[Client] = None,
    *,
    limit: int = 500,
    columns: str = "id, title, keyword_score, abstract",
) -> Any:
    c = client or get_supabase()
    return c.table("papers").select(columns).limit(limit).execute()


def fetch_paper_systems_for_city(
    city_id: str,
    client: Optional[Client] = None,
) -> Any:
    c = client or get_supabase()
    return c.table("paper_systems").select("*").eq("city_id", city_id).execute()


def fetch_visible_researchers(client: Optional[Client] = None) -> Any:
    c = client or get_supabase()
    return c.table("researchers").select("*").eq("is_visible", True).execute()


def update_paper_keyword_score(
    paper_id: str,
    keyword_score: float,
    admin: Optional[Client] = None,
) -> Any:
    """Direct Supabase update. Requires SUPABASE_SERVICE_ROLE_KEY in .env."""
    c = admin or get_supabase_admin()
    return (
        c.table("papers")
        .update({"keyword_score": keyword_score})
        .eq("id", paper_id)
        .execute()
    )


def update_paper_keyword_score_via_rl(paper_id: str, keyword_score: float) -> Any:
    """Update keyword_score through the rl-api edge function (RL_API_KEY)."""
    return rl_update(
        "papers",
        {"keyword_score": keyword_score},
        {"id": paper_id},
    )


def insert_rl_run(
    row: Mapping[str, Any],
    admin: Optional[Client] = None,
) -> Any:
    """Insert a row into rl_runs. Requires service role."""
    c = admin or get_supabase_admin()
    return c.table("rl_runs").insert(dict(row)).execute()


def insert_rl_outputs(
    rows: list[Mapping[str, Any]],
    admin: Optional[Client] = None,
) -> Any:
    """Bulk insert into rl_outputs. Requires service role."""
    c = admin or get_supabase_admin()
    return c.table("rl_outputs").insert([dict(r) for r in rows]).execute()
