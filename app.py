"""
app.py — Reply Agent · Feed page
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
import time

from helpers import (
    GLOBAL_CSS, fetch_user_id, fetch_client_tweets, fetch_target_tweets,
    build_tone_profile, generate_reply, post_reply,
)
from db import (
    log_posted_reply, schedule_reply, fetch_due_scheduled,
    update_scheduled_status,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Reply Agent · Feed", page_icon="💬", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in {
    "client_handle": "",
    "client_user_id": None,
    "tone_profile": None,
    "tweet_count": 0,
    "target_accounts": [],
    "feed": {},
    "posted": set(),
    "last_auto_check": 0.0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Auto-post scheduler (runs on every page load) ─────────────────────────────
def run_scheduler():
    now = time.time()
    if now - st.session_state.last_auto_check < 60:
        return
    st.session_state.last_auto_check = now
    due = fetch_due_scheduled()
    if not due:
        return
    posted_count = 0
    for row in due:
        success = post_reply(row["tweet_id"], row["reply_text"])
        if success:
            update_scheduled_status(row["id"], "posted")
            log_posted_reply(
                client_handle=row["client_handle"],
                tweet_id=row["tweet_id"],
                author_handle=row["author_handle"],
                original_text=row["original_text"],
                reply_text=row["reply_text"],
            )
            posted_count += 1
        else:
            update_scheduled_status(row["id"], "failed", "Auto-post failed")
    if posted_count:
        st.toast(f"⏰ Auto-posted {posted_count} scheduled reply(ies)!", icon="✅")


run_scheduler()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## `Reply Agent`")
    st.markdown("---")

    st.markdown('<div class="section-label">Your X Handle</div>', unsafe_allow_html=True)
    handle_input = st.text_input(
        "handle", value=st.session_state.client_handle,
        placeholder="@yourhandle", label_visibility="collapsed"
    )

    if st.button("Load tone profile", use_container_width=True):
        handle = handle_input.lstrip("@").strip()
        if not handle:
            st.warning("Enter your X handle first.")
        else:
            with st.spinner("Looking up account…"):
                uid = fetch_user_id(handle)
            if uid:
                st.session_state.client_handle = handle
                st.session_state.client_user_id = uid
                with st.spinner("Fetching up to 3,200 of your tweets…"):
                    tweets = fetch_client_tweets(uid)
                if tweets:
                    st.session_state.tweet_count = len(tweets)
                    with st.spinner(f"Analysing {len(tweets)} tweets for tone…"):
                        st.session_state.tone_profile = build_tone_profile(tuple(tweets))
                    st.success(f"Tone profile ready — {len(tweets)} tweets analysed.")
                else:
                    st.warning("No tweets found.")

    if st.session_state.tone_profile:
        st.caption(f"📊 Based on {st.session_state.tweet_count} tweets")
        with st.expander("View tone profile"):
            st.markdown(
                f'<div class="tone-box">{st.session_state.tone_profile}</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    st.markdown('<div class="section-label">Accounts to Monitor</div>', unsafe_allow_html=True)
    new_target = st.text_input("Add", placeholder="@someone", label_visibility="collapsed")

    if st.button("Add account", use_container_width=True):
        t = new_target.lstrip("@").strip()
        existing = [a["handle"] for a in st.session_state.target_accounts]
        if not t:
            st.warning("Enter a handle.")
        elif t in existing:
            st.info(f"@{t} already added.")
        else:
            with st.spinner(f"Looking up @{t}…"):
                uid = fetch_user_id(t)
            if uid:
                st.session_state.target_accounts.append({"handle": t, "user_id": uid})
                st.success(f"Added @{t}")

    for i, acc in enumerate(st.session_state.target_accounts):
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"@{acc['handle']}")
        if c2.button("✕", key=f"rm_{i}"):
            st.session_state.target_accounts.pop(i)
            st.rerun()

    st.markdown("---")
    tweets_per_account = st.slider("Tweets per account", 1, 10, 5)

    if st.button("🔄 Refresh feed", use_container_width=True, type="primary"):
        if not st.session_state.target_accounts:
            st.warning("Add at least one account.")
        elif not st.session_state.tone_profile:
            st.warning("Load your tone profile first.")
        else:
            new_items = {}
            with st.spinner("Fetching latest tweets…"):
                for acc in st.session_state.target_accounts:
                    for t in fetch_target_tweets(acc["user_id"], count=tweets_per_account):
                        tid = t["id"]
                        if tid not in st.session_state.feed:
                            new_items[tid] = {
                                **t,
                                "author_handle": acc["handle"],
                                "reply": None,
                            }
            st.session_state.feed.update(new_items)
            msg = f"{len(new_items)} new tweet(s) loaded." if new_items else "No new tweets."
            st.success(msg) if new_items else st.info(msg)

    st.markdown("---")
    st.page_link("pages/1_📅_Schedule.py", label="📅 Scheduled Replies")
    st.page_link("pages/2_📜_History.py",  label="📜 Post History")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Feed
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 💬 Feed")

if not st.session_state.tone_profile:
    st.info("👈 Load your tone profile in the sidebar to get started.")
    st.stop()

if not st.session_state.target_accounts:
    st.info("👈 Add accounts to monitor, then click **Refresh feed**.")
    st.stop()

if not st.session_state.feed:
    st.info("Click **Refresh feed** in the sidebar to load tweets.")
    st.stop()

sorted_feed = sorted(
    st.session_state.feed.items(),
    key=lambda x: x[1].get("created_at", ""),
    reverse=True,
)

for tweet_id, item in sorted_feed:
    date_str = item.get("created_at", "")[:10]
    st.markdown(f"""
    <div class="tweet-card">
        <div class="tweet-author">@{item['author_handle']} · {date_str}</div>
        <div class="tweet-text">{item['text']}</div>
    </div>
    """, unsafe_allow_html=True)

    col_gen, _ = st.columns([2, 5])
    with col_gen:
        if st.button("✨ Generate reply", key=f"gen_{tweet_id}"):
            with st.spinner("Writing reply…"):
                reply = generate_reply(
                    tweet_text=item["text"],
                    tone_profile=st.session_state.tone_profile,
                    author_handle=item["author_handle"],
                )
            st.session_state.feed[tweet_id]["reply"] = reply
            st.rerun()

    if item.get("reply"):
        reply_text = item["reply"]
        char_count = len(reply_text)
        color = "#5db85d" if char_count <= 270 else "#e05c5c"

        st.markdown(f'<div class="reply-box">{reply_text}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<span style="font-size:11px;color:{color};font-family:monospace">{char_count}/270 chars</span>',
            unsafe_allow_html=True,
        )

        edited = st.text_area(
            "Edit", value=reply_text, key=f"edit_{tweet_id}",
            height=80, label_visibility="collapsed",
        )
        st.session_state.feed[tweet_id]["reply"] = edited

        col_copy, col_post, col_sched, col_regen = st.columns([2, 2, 2, 2])

        with col_copy:
            st.markdown(
                f"""<button onclick="navigator.clipboard.writeText({repr(edited)});
                    this.innerText='✅ Copied!';setTimeout(()=>this.innerText='📋 Copy',1500)"
                    style="width:100%;padding:8px 0;background:#1e1e1e;border:1px solid #333;
                           border-radius:6px;color:#e0e0e0;cursor:pointer;font-size:13px;">
                    📋 Copy
                </button>""",
                unsafe_allow_html=True,
            )

        with col_post:
            if tweet_id in st.session_state.posted:
                st.markdown('<span class="status-pill pill-posted">✓ Posted</span>', unsafe_allow_html=True)
            else:
                if st.button("🚀 Post now", key=f"post_{tweet_id}"):
                    with st.spinner("Posting…"):
                        ok = post_reply(tweet_id, edited)
                    if ok:
                        st.session_state.posted.add(tweet_id)
                        log_posted_reply(
                            client_handle=st.session_state.client_handle,
                            tweet_id=tweet_id,
                            author_handle=item["author_handle"],
                            original_text=item["text"],
                            reply_text=edited,
                        )
                        st.success("Posted!")
                        st.rerun()

        with col_sched:
            if st.button("⏰ Schedule", key=f"sched_btn_{tweet_id}"):
                st.session_state[f"show_sched_{tweet_id}"] = not st.session_state.get(f"show_sched_{tweet_id}", False)

        with col_regen:
            if st.button("🔁 Regen", key=f"regen_{tweet_id}"):
                with st.spinner("Rewriting…"):
                    new_reply = generate_reply(
                        tweet_text=item["text"],
                        tone_profile=st.session_state.tone_profile,
                        author_handle=item["author_handle"],
                    )
                st.session_state.feed[tweet_id]["reply"] = new_reply
                st.rerun()

        # Inline scheduler
        if st.session_state.get(f"show_sched_{tweet_id}"):
            sc1, sc2, sc3 = st.columns([2, 2, 2])
            with sc1:
                sched_date = st.date_input(
                    "Date", value=datetime.now().date() + timedelta(days=1),
                    key=f"sdate_{tweet_id}",
                )
            with sc2:
                sched_time = st.time_input(
                    "Time (UTC)", value=datetime.now().time(),
                    key=f"stime_{tweet_id}",
                )
            with sc3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✅ Confirm", key=f"conf_{tweet_id}"):
                    scheduled_dt = datetime.combine(sched_date, sched_time, tzinfo=timezone.utc)
                    ok = schedule_reply(
                        client_handle=st.session_state.client_handle,
                        tweet_id=tweet_id,
                        author_handle=item["author_handle"],
                        original_text=item["text"],
                        reply_text=edited,
                        scheduled_for=scheduled_dt,
                    )
                    if ok:
                        st.success(f"Scheduled for {scheduled_dt.strftime('%b %d, %H:%M')} UTC")
                        st.session_state[f"show_sched_{tweet_id}"] = False
                        st.rerun()

    st.markdown("---")
