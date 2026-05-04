"""
db.py — Supabase database layer for Reply Agent.

Tables (run setup_sql() output in Supabase SQL editor once):
  reply_history — every generated reply
"""

from __future__ import annotations
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone


# ── Client ─────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA (paste into Supabase SQL editor once)
# ══════════════════════════════════════════════════════════════════════════════
SETUP_SQL = """
create table if not exists reply_history (
    id              bigint generated always as identity primary key,
    client_handle   text not null,
    tweet_id        text not null,
    author_handle   text not null,
    original_text   text not null,
    reply_text      text not null,
    posted_at       timestamptz not null default now()
);

create index if not exists idx_history_client     on reply_history(client_handle);
create index if not exists idx_history_posted_at  on reply_history(posted_at desc);
"""


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════════════
def log_generated_reply(
    client_handle: str,
    tweet_id: str,
    author_handle: str,
    original_text: str,
    reply_text: str,
) -> bool:
    try:
        get_supabase().table("reply_history").insert({
            "client_handle": client_handle,
            "tweet_id": tweet_id,
            "author_handle": author_handle,
            "original_text": original_text,
            "reply_text": reply_text,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:
        st.error(f"DB error logging reply: {e}")
        return False


def fetch_history(
    client_handle: str | None = None,
    author_handle: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict]:
    try:
        q = get_supabase().table("reply_history").select("*").order("posted_at", desc=True).limit(limit)
        if client_handle:
            q = q.eq("client_handle", client_handle)
        if author_handle:
            q = q.eq("author_handle", author_handle)
        resp = q.execute()
        rows = resp.data or []
        if search:
            s = search.lower()
            rows = [r for r in rows if s in r["original_text"].lower() or s in r["reply_text"].lower()]
        return rows
    except Exception as e:
        st.error(f"DB error fetching history: {e}")
        return []
