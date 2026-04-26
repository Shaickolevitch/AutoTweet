"""
pages/1_📅_Schedule.py — Scheduled replies management page
"""

import streamlit as st
from datetime import datetime, timezone, timedelta

from helpers import GLOBAL_CSS, post_reply
from db import (
    fetch_scheduled, update_scheduled_status,
    update_scheduled_reply_text, update_scheduled_time,
    log_posted_reply,
)

st.set_page_config(page_title="Reply Agent · Schedule", page_icon="📅", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

st.markdown("# 📅 Scheduled Replies")

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════
with st.container():
    f1, f2, f3, f4 = st.columns([3, 2, 2, 2])

    with f1:
        search = st.text_input("🔍 Search", placeholder="keyword in tweet or reply…", label_visibility="collapsed")

    with f2:
        status_filter = st.selectbox(
            "Status",
            ["all", "pending", "posted", "failed", "cancelled"],
            label_visibility="collapsed",
        )

    with f3:
        author_filter = st.text_input("Filter by account", placeholder="@account", label_visibility="collapsed")

    with f4:
        sort_order = st.selectbox("Sort", ["Soonest first", "Latest first", "Newest created"], label_visibility="collapsed")

st.markdown("---")

# ── Fetch ──────────────────────────────────────────────────────────────────────
rows = fetch_scheduled(
    status=status_filter if status_filter != "all" else None,
    author_handle=author_filter.lstrip("@").strip() if author_filter else None,
    search=search if search else None,
)

# ── Sort ───────────────────────────────────────────────────────────────────────
if sort_order == "Soonest first":
    rows.sort(key=lambda r: r["scheduled_for"])
elif sort_order == "Latest first":
    rows.sort(key=lambda r: r["scheduled_for"], reverse=True)
else:
    rows.sort(key=lambda r: r["created_at"], reverse=True)

# ── Stats bar ──────────────────────────────────────────────────────────────────
all_rows = fetch_scheduled()
counts = {s: sum(1 for r in all_rows if r["status"] == s) for s in ["pending", "posted", "failed", "cancelled"]}

s1, s2, s3, s4, s5 = st.columns(5)
s1.markdown(f'<div class="stat-card"><div class="stat-num">{len(all_rows)}</div><div class="stat-label">Total</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#c8b84a">{counts["pending"]}</div><div class="stat-label">Pending</div></div>', unsafe_allow_html=True)
s3.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#5db85d">{counts["posted"]}</div><div class="stat-label">Posted</div></div>', unsafe_allow_html=True)
s4.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#c85d5d">{counts["failed"]}</div><div class="stat-label">Failed</div></div>', unsafe_allow_html=True)
s5.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#777">{counts["cancelled"]}</div><div class="stat-label">Cancelled</div></div>', unsafe_allow_html=True)

st.markdown(f"<br><span style='color:#555;font-size:13px;font-family:monospace'>Showing {len(rows)} result(s)</span>", unsafe_allow_html=True)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# ROWS
# ══════════════════════════════════════════════════════════════════════════════
if not rows:
    st.info("No scheduled replies match your filters.")
    st.stop()

STATUS_PILL = {
    "pending":   '<span class="status-pill pill-pending">⏳ Pending</span>',
    "posted":    '<span class="status-pill pill-posted">✓ Posted</span>',
    "failed":    '<span class="status-pill pill-failed">✗ Failed</span>',
    "cancelled": '<span class="status-pill pill-cancelled">— Cancelled</span>',
}

now_utc = datetime.now(timezone.utc)

for row in rows:
    row_id = row["id"]
    scheduled_dt = datetime.fromisoformat(row["scheduled_for"])
    if scheduled_dt.tzinfo is None:
        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)

    is_overdue = row["status"] == "pending" and scheduled_dt < now_utc
    border_color = "#5a2a2a" if is_overdue else "#2a2a2a"

    pill = STATUS_PILL.get(row["status"], "")
    sched_str = scheduled_dt.strftime("%b %d, %Y · %H:%M UTC")
    overdue_tag = ' <span style="color:#c85d5d;font-size:11px;font-family:monospace">(OVERDUE)</span>' if is_overdue else ""

    st.markdown(f"""
    <div class="tweet-card" style="border-color:{border_color}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <div>
                <span class="tweet-author">@{row['author_handle']}</span>
                &nbsp;·&nbsp;
                <span style="font-family:monospace;font-size:12px;color:#666">⏰ {sched_str}{overdue_tag}</span>
            </div>
            {pill}
        </div>
        <div style="font-size:13px;color:#888;margin-bottom:8px;border-left:2px solid #333;padding-left:10px">
            {row['original_text'][:200]}{'…' if len(row['original_text']) > 200 else ''}
        </div>
        <div class="reply-box" style="margin-bottom:0">{row['reply_text']}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Actions ────────────────────────────────────────────────────────────────
    if row["status"] == "pending":
        with st.expander("✏️ Edit / Actions", expanded=is_overdue):
            ea, eb = st.columns([4, 2])

            with ea:
                new_text = st.text_area(
                    "Reply text", value=row["reply_text"],
                    key=f"edit_text_{row_id}", height=80, label_visibility="collapsed",
                )
                tc1, tc2 = st.columns(2)
                with tc1:
                    if st.button("💾 Save text", key=f"save_text_{row_id}"):
                        if update_scheduled_reply_text(row_id, new_text):
                            st.success("Saved.")
                            st.rerun()

            with eb:
                st.markdown("**Reschedule**")
                new_date = st.date_input("New date", value=scheduled_dt.date(), key=f"ndate_{row_id}")
                new_time = st.time_input("New time (UTC)", value=scheduled_dt.time(), key=f"ntime_{row_id}")
                if st.button("📅 Reschedule", key=f"resched_{row_id}"):
                    new_dt = datetime.combine(new_date, new_time, tzinfo=timezone.utc)
                    if update_scheduled_time(row_id, new_dt):
                        st.success(f"Rescheduled to {new_dt.strftime('%b %d, %H:%M')} UTC")
                        st.rerun()

            col_post, col_cancel = st.columns([2, 2])
            with col_post:
                if st.button("🚀 Post now", key=f"post_now_{row_id}", type="primary"):
                    client_handle = st.session_state.get("client_handle", row.get("client_handle", ""))
                    with st.spinner("Posting…"):
                        ok = post_reply(row["tweet_id"], row["reply_text"])
                    if ok:
                        update_scheduled_status(row_id, "posted")
                        log_posted_reply(
                            client_handle=row["client_handle"],
                            tweet_id=row["tweet_id"],
                            author_handle=row["author_handle"],
                            original_text=row["original_text"],
                            reply_text=row["reply_text"],
                        )
                        st.success("Posted!")
                        st.rerun()

            with col_cancel:
                if st.button("🚫 Cancel", key=f"cancel_{row_id}"):
                    update_scheduled_status(row_id, "cancelled")
                    st.rerun()

    elif row["status"] == "failed":
        with st.expander("🔁 Retry"):
            if st.button("Retry post", key=f"retry_{row_id}", type="primary"):
                with st.spinner("Posting…"):
                    ok = post_reply(row["tweet_id"], row["reply_text"])
                if ok:
                    update_scheduled_status(row_id, "posted")
                    log_posted_reply(
                        client_handle=row["client_handle"],
                        tweet_id=row["tweet_id"],
                        author_handle=row["author_handle"],
                        original_text=row["original_text"],
                        reply_text=row["reply_text"],
                    )
                    st.success("Posted!")
                    st.rerun()
                else:
                    update_scheduled_status(row_id, "failed", "Retry also failed")

    st.markdown("")
