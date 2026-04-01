# -------------------------------------- #
# Project:          CCAS
# RL dataset API — calls Lovable / Supabase edge function `rl-api`.
# Auth: header x-rl-api-key (set RL_API_KEY in .env; never commit secrets).
# -------------------------------------- #

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Optional

import requests
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

_RL_TABLES = frozenset({"papers", "paper_systems", "researchers"})


def _require_rl_key() -> str:
    value = os.environ.get("RL_API_KEY")
    if value is None or not str(value).strip():
        raise ValueError(
            f"Missing RL_API_KEY. Set it in {_ENV_PATH} (Cloud → Secrets → RL_API_KEY)."
        )
    return str(value).strip().strip('"')


def default_rl_api_url() -> str:
    """Edge function URL; override with RL_API_URL if your project ref differs."""
    return os.environ.get("RL_API_URL") or (
        "https://hoizypsxgoqtwecugqyy.supabase.co/functions/v1/rl-api"
    )


def _check_table(name: str) -> None:
    if name not in _RL_TABLES:
        raise ValueError(
            f"table must be one of {sorted(_RL_TABLES)}, got {name!r}"
        )


def call_rl_api(
    body: Mapping[str, Any],
    *,
    timeout_s: float = 120.0,
) -> Any:
    """
    POST JSON to the rl-api edge function. Use this if the helpers below
    do not match the deployed request shape — pass the exact payload your
    function expects.
    """
    url = default_rl_api_url()
    key = _require_rl_key()
    resp = requests.post(
        url,
        json=dict(body),
        headers={
            "Content-Type": "application/json",
            "x-rl-api-key": key,
        },
        timeout=timeout_s,
    )
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}
    if not resp.ok:
        raise RuntimeError(
            f"rl-api HTTP {resp.status_code}: {data!r}"
        )
    return data


def rl_select(
    table: str,
    *,
    columns: str = "*",
    limit: Optional[int] = None,
    filters: Optional[Mapping[str, Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Any:
    """
    action=select. Request body matches common rl-api patterns; if your
    deployed function uses different field names, use call_rl_api() or
    pass overrides via `extra`.
    """
    _check_table(table)
    body: dict[str, Any] = {
        "action": "select",
        "table": table,
        "columns": columns,
    }
    if limit is not None:
        body["limit"] = limit
    if filters:
        body["filters"] = dict(filters)
    if extra:
        body.update(dict(extra))
    return call_rl_api(body)


def rl_insert(
    table: str,
    record: Mapping[str, Any],
    *,
    extra: Optional[Mapping[str, Any]] = None,
) -> Any:
    _check_table(table)
    body: dict[str, Any] = {
        "action": "insert",
        "table": table,
        "record": dict(record),
    }
    if extra:
        body.update(dict(extra))
    return call_rl_api(body)


def rl_update(
    table: str,
    record: Mapping[str, Any],
    match: Mapping[str, Any],
    *,
    extra: Optional[Mapping[str, Any]] = None,
) -> Any:
    """Update rows where columns in `match` equal the given values."""
    _check_table(table)
    body: dict[str, Any] = {
        "action": "update",
        "table": table,
        "record": dict(record),
        "match": dict(match),
    }
    if extra:
        body.update(dict(extra))
    return call_rl_api(body)
