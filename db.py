"""
db.py — Supabase database layer for Reply Agent.

Tables (run setup_sql() output in Supabase SQL editor once):
  reply_history      — every successfully posted reply
  scheduled_replies  — queue of replies waiting to be posted
"""

from __future__ import annotations
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone
from typing import Literal


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
-- Reply history
create table if not exists reply_history (
    id              bigint generated always as identity primary key,
    client_handle   text not null,
    tweet_id        text not null,
    author_handle   text not null,
    original_text   text not null,
    reply_text      text not null,
    posted_at       timestamptz not null default now()
);

-- Scheduled replies
create table if not exists scheduled_replies (
    id              bigint generated always as identity primary key,
    client_handle   text not null,
    tweet_id        text not null,
    author_handle   text not null,
    original_text   text not null,
    reply_text      text not null,
    scheduled_for   timestamptz not null,
    status          text not null default 'pending',  -- pending | posted | failed | cancelled
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    error_message   text
);

create index if not exists idx_scheduled_status   on scheduled_replies(status);
create index if not exists idx_scheduled_for      on scheduled_replies(scheduled_for);
create index if not exists idx_history_client     on reply_history(client_handle);
create index if not exists idx_history_posted_at  on reply_history(posted_at desc);
"""


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════════════
def log_posted_reply(
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


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULED REPLIES
# ══════════════════════════════════════════════════════════════════════════════
def schedule_reply(
    client_handle: str,
    tweet_id: str,
    author_handle: str,
    original_text: str,
    reply_text: str,
    scheduled_for: datetime,
) -> bool:
    try:
        get_supabase().table("scheduled_replies").insert({
            "client_handle": client_handle,
            "tweet_id": tweet_id,
            "author_handle": author_handle,
            "original_text": original_text,
            "reply_text": reply_text,
            "scheduled_for": scheduled_for.isoformat(),
            "status": "pending",
        }).execute()
        return True
    except Exception as e:
        st.error(f"DB error scheduling reply: {e}")
        return False


def fetch_scheduled(
    client_handle: str | None = None,
    status: str | None = None,
    author_handle: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[dict]:
    try:
        q = get_supabase().table("scheduled_replies").select("*").order("scheduled_for").limit(limit)
        if client_handle:
            q = q.eq("client_handle", client_handle)
        if status and status != "all":
            q = q.eq("status", status)
        if author_handle:
            q = q.eq("author_handle", author_handle)
        resp = q.execute()
        rows = resp.data or []
        if search:
            s = search.lower()
            rows = [r for r in rows if s in r["original_text"].lower() or s in r["reply_text"].lower() or s in r["author_handle"].lower()]
        return rows
    except Exception as e:
        st.error(f"DB error fetching scheduled: {e}")
        return []


def fetch_due_scheduled() -> list[dict]:
    """Return pending replies whose scheduled_for <= now."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        resp = (
            get_supabase()
            .table("scheduled_replies")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_for", now)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        st.error(f"DB error fetching due scheduled: {e}")
        return []


def update_scheduled_status(
    row_id: int,
    status: Literal["posted", "failed", "cancelled", "pending"],
    error_message: str | None = None,
) -> bool:
    try:
        payload = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if error_message:
            payload["error_message"] = error_message
        get_supabase().table("scheduled_replies").update(payload).eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"DB error updating scheduled: {e}")
        return False


def update_scheduled_reply_text(row_id: int, new_text: str) -> bool:
    try:
        get_supabase().table("scheduled_replies").update({
            "reply_text": new_text,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"DB error updating reply text: {e}")
        return False


def update_scheduled_time(row_id: int, new_time: datetime) -> bool:
    try:
        get_supabase().table("scheduled_replies").update({
            "scheduled_for": new_time.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"DB error updating scheduled time: {e}")
        return False
