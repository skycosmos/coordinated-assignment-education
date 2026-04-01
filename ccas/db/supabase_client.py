# -------------------------------------- #
# Project:          CCAS
# Supabase client factory (anon + service role).
# Loads SUPABASE_* from .env at repository root.
#
# Also used by the RL stack (see rl_api_client.py):
#   RL_API_URL   — optional; defaults to project rl-api edge function URL
#   RL_API_KEY   — secret for x-rl-api-key (writes to papers / paper_systems / researchers)
# -------------------------------------- #

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

from ccas.paths import REPO_ROOT, load_env

_ENV_PATH = REPO_ROOT / ".env"
load_env()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        raise ValueError(
            f"Missing or empty {name}. Set it in {_ENV_PATH} (see SUPABASE_* variables)."
        )
    return str(value).strip().strip('"')


def get_supabase() -> Client:
    """Read-only client (anon key). Respects RLS; use for SELECT."""
    url = _require_env("SUPABASE_URL")
    key = _require_env("SUPABASE_ANON_KEY")
    return create_client(url, key)


def get_supabase_admin() -> Client:
    """Admin client (service role). Bypasses RLS; use only on trusted servers."""
    url = _require_env("SUPABASE_URL")
    key = _require_env("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)
