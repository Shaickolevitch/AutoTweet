"""
pages/2_📜_History.py — היסטוריית תגובות שנוצרו
"""

import streamlit as st
from datetime import datetime

from helpers import GLOBAL_CSS, TOMER_HANDLE, TOMER_NAME_HE
from db import fetch_history

st.set_page_config(page_title=f"{TOMER_NAME_HE} · היסטוריה", page_icon="📜", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

st.markdown(f"""
<div class="page-title">
    📜 היסטוריית תגובות <span>· {TOMER_NAME_HE}</span>
</div>
""", unsafe_allow_html=True)

# ── Filters ────────────────────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns([3, 2, 2, 1])
with f1:
    search = st.text_input("🔍 חיפוש", placeholder="חיפוש בציוץ או תגובה...", label_visibility="collapsed")
with f2:
    author_filter = st.text_input("סינון לפי @חשבון", placeholder="@account", label_visibility="collapsed")
with f3:
    limit = st.selectbox("הצג אחרונים", [25, 50, 100, 250], label_visibility="collapsed")
with f4:
    sort_dir = st.selectbox("מיון", ["חדש לישן", "ישן לחדש"], label_visibility="collapsed")

st.markdown("---")

# ── Fetch ──────────────────────────────────────────────────────────────────────
rows = fetch_history(
    client_handle=TOMER_HANDLE,
    author_handle=author_filter.lstrip("@").strip() if author_filter else None,
    search=search if search else None,
    limit=limit,
)

if sort_dir == "ישן לחדש":
    rows = list(reversed(rows))

# ── Stats ──────────────────────────────────────────────────────────────────────
all_rows = fetch_history(client_handle=TOMER_HANDLE, limit=10000)
unique_accounts = len(set(r["author_handle"] for r in all_rows))

s1, s2, s3 = st.columns(3)
s1.markdown(f'<div class="stat-card"><div class="stat-num">{len(all_rows)}</div><div class="stat-label">סה"כ תגובות שנוצרו</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="stat-card"><div class="stat-num">{unique_accounts}</div><div class="stat-label">חשבונות שנוצרו תגובות עבורם</div></div>', unsafe_allow_html=True)
if all_rows:
    latest = all_rows[0]["posted_at"][:10]
    s3.markdown(f'<div class="stat-card"><div class="stat-num" style="font-size:20px">{latest}</div><div class="stat-label">פעילות אחרונה</div></div>', unsafe_allow_html=True)

st.markdown(f"<br><span style='color:#555;font-size:12px;font-family:monospace'>מציג {len(rows)} תוצאות</span>", unsafe_allow_html=True)
st.markdown("---")

# ── View toggle ────────────────────────────────────────────────────────────────
view_mode = st.radio("תצוגה", ["כרטיסיות", "טבלה"], horizontal=True, label_visibility="collapsed")

if not rows:
    st.info("אין היסטוריה עדיין. צור תגובות כדי לראות אותן כאן.")
    st.stop()

if view_mode == "טבלה":
    import pandas as pd
    df = pd.DataFrame(rows)[["posted_at", "author_handle", "original_text", "reply_text"]]
    df["posted_at"] = pd.to_datetime(df["posted_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df.columns = ["תאריך יצירה", "חשבון", "ציוץ מקורי", "תגובה"]
    st.dataframe(df, use_container_width=True, height=600)
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 הורד CSV",
        data=csv,
        file_name=f"history_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    for row in rows:
        generated_dt = row["posted_at"][:16].replace("T", " ")
        is_hebrew = any("֐" <= c <= "׿" for c in row["original_text"])
        text_class = "tweet-text" if is_hebrew else "tweet-text-ltr"

        st.markdown(f"""
        <div class="tweet-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <span class="tweet-author">@{row['author_handle']}</span>
                <span style="font-family:monospace;font-size:11px;color:#555">📅 {generated_dt} UTC</span>
            </div>
            <div class="{text_class}" style="font-size:13px;color:#888;margin-bottom:10px;
                        border-right:2px solid #333;padding-right:10px;">
                {row['original_text'][:300]}{'...' if len(row['original_text']) > 300 else ''}
            </div>
            <div class="reply-box" style="margin-bottom:0">
                {row['reply_text']}
            </div>
        </div>
        """, unsafe_allow_html=True)
