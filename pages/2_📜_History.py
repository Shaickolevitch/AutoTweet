"""
pages/2_📜_History.py — Reply history page
"""

import streamlit as st
from datetime import datetime, timezone

from helpers import GLOBAL_CSS
from db import fetch_history

st.set_page_config(page_title="Reply Agent · History", page_icon="📜", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

st.markdown("# 📜 Post History")

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════
f1, f2, f3, f4 = st.columns([3, 2, 2, 1])

with f1:
    search = st.text_input("🔍 Search", placeholder="keyword in tweet or reply…", label_visibility="collapsed")
with f2:
    author_filter = st.text_input("Filter by @account", placeholder="@account", label_visibility="collapsed")
with f3:
    limit = st.selectbox("Show last", [25, 50, 100, 250, 500], label_visibility="collapsed")
with f4:
    sort_dir = st.selectbox("Sort", ["Newest", "Oldest"], label_visibility="collapsed")

st.markdown("---")

# ── Fetch ──────────────────────────────────────────────────────────────────────
rows = fetch_history(
    client_handle=st.session_state.get("client_handle") or None,
    author_handle=author_filter.lstrip("@").strip() if author_filter else None,
    search=search if search else None,
    limit=limit,
)

if sort_dir == "Oldest":
    rows = list(reversed(rows))

# ── Stats ──────────────────────────────────────────────────────────────────────
all_rows = fetch_history(limit=10000)
unique_accounts = len(set(r["author_handle"] for r in all_rows))

s1, s2, s3 = st.columns(3)
s1.markdown(f'<div class="stat-card"><div class="stat-num">{len(all_rows)}</div><div class="stat-label">Total Replies Posted</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="stat-card"><div class="stat-num">{unique_accounts}</div><div class="stat-label">Unique Accounts Engaged</div></div>', unsafe_allow_html=True)

if all_rows:
    latest = all_rows[0]["posted_at"][:10]
    s3.markdown(f'<div class="stat-card"><div class="stat-num" style="font-size:18px">{latest}</div><div class="stat-label">Last Activity</div></div>', unsafe_allow_html=True)

st.markdown(f"<br><span style='color:#555;font-size:13px;font-family:monospace'>Showing {len(rows)} result(s)</span>", unsafe_allow_html=True)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABLE + CARDS
# ══════════════════════════════════════════════════════════════════════════════
view_mode = st.radio("View", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

if not rows:
    st.info("No history found. Post some replies first!")
    st.stop()

if view_mode == "Table":
    import pandas as pd
    df = pd.DataFrame(rows)[["posted_at", "author_handle", "original_text", "reply_text", "client_handle"]]
    df["posted_at"] = pd.to_datetime(df["posted_at"]).dt.strftime("%Y-%m-%d %H:%M UTC")
    df.columns = ["Posted At", "Author", "Original Tweet", "Reply", "Client"]
    st.dataframe(df, use_container_width=True, height=600)

    # CSV download
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        data=csv,
        file_name=f"reply_history_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

else:
    for row in rows:
        posted_dt = row["posted_at"][:16].replace("T", " ")

        st.markdown(f"""
        <div class="tweet-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <span class="tweet-author">@{row['author_handle']}</span>
                <span style="font-family:monospace;font-size:11px;color:#555">📅 {posted_dt} UTC</span>
            </div>
            <div style="font-size:13px;color:#888;margin-bottom:10px;
                        border-left:2px solid #333;padding-left:10px;line-height:1.5">
                {row['original_text'][:300]}{'…' if len(row['original_text']) > 300 else ''}
            </div>
            <div class="reply-box" style="margin-bottom:0">
                {row['reply_text']}
            </div>
        </div>
        """, unsafe_allow_html=True)
