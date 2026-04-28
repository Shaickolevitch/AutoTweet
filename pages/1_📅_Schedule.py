"""
pages/1_📅_Schedule.py — תגובות מתוזמנות
"""

import streamlit as st
from datetime import datetime, timezone

from helpers import GLOBAL_CSS, TOMER_HANDLE, TOMER_NAME_HE, post_reply
from db import (
    fetch_scheduled, update_scheduled_status,
    update_scheduled_reply_text, update_scheduled_time,
    log_posted_reply,
)

st.set_page_config(page_title=f"{TOMER_NAME_HE} · תגובות מתוזמנות", page_icon="📅", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

st.markdown(f"""
<div class="page-title">
    📅 תגובות מתוזמנות <span>· {TOMER_NAME_HE}</span>
</div>
""", unsafe_allow_html=True)

# ── Filters ────────────────────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
with f1:
    search = st.text_input("🔍 חיפוש", placeholder="מילת חיפוש בציוץ או תגובה...", label_visibility="collapsed")
with f2:
    status_filter = st.selectbox("סטטוס", ["הכל", "draft", "pending", "posted", "failed", "cancelled"], label_visibility="collapsed")
with f3:
    author_filter = st.text_input("סינון לפי חשבון", placeholder="@account", label_visibility="collapsed")
with f4:
    sort_order = st.selectbox("מיון", ["הקרוב ביותר", "המאוחר ביותר", "חדש ביותר"], label_visibility="collapsed")

st.markdown("---")

# ── Fetch ──────────────────────────────────────────────────────────────────────
status_map = {"הכל": None, "draft": "draft", "pending": "pending", "posted": "posted", "failed": "failed", "cancelled": "cancelled"}
rows = fetch_scheduled(
    client_handle=TOMER_HANDLE,
    status=status_map.get(status_filter),
    author_handle=author_filter.lstrip("@").strip() if author_filter else None,
    search=search if search else None,
)

if sort_order == "הקרוב ביותר":
    rows.sort(key=lambda r: r["scheduled_for"])
elif sort_order == "המאוחר ביותר":
    rows.sort(key=lambda r: r["scheduled_for"], reverse=True)
else:
    rows.sort(key=lambda r: r["created_at"], reverse=True)

# ── Stats ──────────────────────────────────────────────────────────────────────
all_rows = fetch_scheduled(client_handle=TOMER_HANDLE)
counts = {s: sum(1 for r in all_rows if r["status"] == s) for s in ["draft", "pending", "posted", "failed", "cancelled"]}

s1, s2, s3, s4, s5, s6 = st.columns(6)
s1.markdown(f'<div class="stat-card"><div class="stat-num">{len(all_rows)}</div><div class="stat-label">סה"כ</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#60a5fa">{counts["draft"]}</div><div class="stat-label">טיוטות</div></div>', unsafe_allow_html=True)
s3.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#fbbf24">{counts["pending"]}</div><div class="stat-label">ממתינות</div></div>', unsafe_allow_html=True)
s4.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#4ade80">{counts["posted"]}</div><div class="stat-label">פורסמו</div></div>', unsafe_allow_html=True)
s5.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#f87171">{counts["failed"]}</div><div class="stat-label">נכשלו</div></div>', unsafe_allow_html=True)
s6.markdown(f'<div class="stat-card"><div class="stat-num" style="color:#777">{counts["cancelled"]}</div><div class="stat-label">בוטלו</div></div>', unsafe_allow_html=True)

st.markdown(f"<br><span style='color:#555;font-size:12px;font-family:monospace'>מציג {len(rows)} תוצאות</span>", unsafe_allow_html=True)
st.markdown("---")

if not rows:
    st.info("אין תגובות מתוזמנות שמתאימות לסינון.")
    st.stop()

# ── Status pills ───────────────────────────────────────────────────────────────
STATUS_PILL = {
    "draft":     '<span class="status-pill pill-draft">✏️ טיוטה</span>',
    "pending":   '<span class="status-pill pill-pending">⏳ ממתין</span>',
    "posted":    '<span class="status-pill pill-posted">✓ פורסם</span>',
    "failed":    '<span class="status-pill pill-failed">✗ נכשל</span>',
    "cancelled": '<span class="status-pill pill-cancelled">— בוטל</span>',
}

now_utc = datetime.now(timezone.utc)

for row in rows:
    row_id = row["id"]
    scheduled_dt = datetime.fromisoformat(row["scheduled_for"])
    if scheduled_dt.tzinfo is None:
        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
    is_overdue = row["status"] == "pending" and scheduled_dt < now_utc
    sched_str = scheduled_dt.strftime("%d/%m/%Y · %H:%M UTC")
    overdue_tag = ' <span style="color:#f87171;font-size:11px">(באיחור!)</span>' if is_overdue else ""
    pill = STATUS_PILL.get(row["status"], "")

    st.markdown(f"""
    <div class="tweet-card" style="border-left-color:{'#f87171' if is_overdue else '#e94560'}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <div>
                <span class="tweet-author">@{row['author_handle']}</span>
                &nbsp;·&nbsp;
                <span style="font-family:monospace;font-size:11px;color:#666">⏰ {sched_str}{overdue_tag}</span>
            </div>
            {pill}
        </div>
        <div style="font-size:13px;color:#888;margin-bottom:8px;border-right:2px solid #333;padding-right:10px;direction:rtl;text-align:right">
            {row['original_text'][:200]}{'...' if len(row['original_text']) > 200 else ''}
        </div>
        <div class="reply-box" style="margin-bottom:0">{row['reply_text']}</div>
    </div>
    """, unsafe_allow_html=True)

    if row["status"] in ("pending", "draft"):
        with st.expander("✏️ עריכה ופעולות", expanded=is_overdue):
            ea, eb = st.columns([4, 2])
            with ea:
                new_text = st.text_area("טקסט תגובה", value=row["reply_text"], key=f"edit_{row_id}", height=80, label_visibility="collapsed")
                if st.button("💾 שמור", key=f"save_{row_id}"):
                    if update_scheduled_reply_text(row_id, new_text):
                        st.success("נשמר")
                        st.rerun()
            with eb:
                st.markdown("**תזמון מחדש**")
                new_date = st.date_input("תאריך", value=scheduled_dt.date(), key=f"ndate_{row_id}")
                new_time = st.time_input("שעה (UTC)", value=scheduled_dt.time(), key=f"ntime_{row_id}")
                if st.button("📅 עדכן תזמון", key=f"resched_{row_id}"):
                    new_dt = datetime.combine(new_date, new_time, tzinfo=timezone.utc)
                    if update_scheduled_time(row_id, new_dt):
                        st.success(f"עודכן ל-{new_dt.strftime('%d/%m %H:%M')}")
                        st.rerun()

            col_post, col_cancel = st.columns(2)
            with col_post:
                if st.button("🚀 פרסם עכשיו", key=f"post_now_{row_id}", type="primary"):
                    with st.spinner("מפרסם..."):
                        ok = post_reply(row["tweet_id"], row["reply_text"])
                    if ok:
                        update_scheduled_status(row_id, "posted")
                        log_posted_reply(
                            client_handle=TOMER_HANDLE,
                            tweet_id=row["tweet_id"],
                            author_handle=row["author_handle"],
                            original_text=row["original_text"],
                            reply_text=row["reply_text"],
                        )
                        st.success("✅ פורסם!")
                        st.rerun()
            with col_cancel:
                if st.button("🚫 בטל", key=f"cancel_{row_id}"):
                    update_scheduled_status(row_id, "cancelled")
                    st.rerun()

    elif row["status"] == "failed":
        with st.expander("🔁 נסה שוב"):
            if st.button("נסה לפרסם שוב", key=f"retry_{row_id}", type="primary"):
                with st.spinner("מפרסם..."):
                    ok = post_reply(row["tweet_id"], row["reply_text"])
                if ok:
                    update_scheduled_status(row_id, "posted")
                    log_posted_reply(TOMER_HANDLE, row["tweet_id"], row["author_handle"], row["original_text"], row["reply_text"])
                    st.success("✅ פורסם!")
                    st.rerun()

    st.markdown("")
