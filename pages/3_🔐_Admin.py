"""
pages/3_🔐_Admin.py — Admin access log viewer
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from helpers import GLOBAL_CSS, TOMER_NAME_HE, TOMER_HANDLE
from db import fetch_access_log

st.set_page_config(page_title="Admin · Access Log", page_icon="🔐", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

_ADMIN_PASSWORD = "TomerAdmin2026!"

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#141414;border:1px solid #333;border-radius:12px;
                    padding:32px 28px;text-align:center;margin-bottom:24px;">
            <div style="font-family:Heebo,sans-serif;font-size:20px;font-weight:900;
                        color:#ffffff;">🔐 Admin</div>
        </div>
        """, unsafe_allow_html=True)
        pwd = st.text_input("סיסמת אדמין", type="password", key="admin_pwd")
        if st.button("כניסה", use_container_width=True, type="primary"):
            if pwd == _ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("סיסמה שגויה")
    st.stop()

# ── Admin view ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-title">🔐 Access Log <span>· {TOMER_NAME_HE}</span></div>
""", unsafe_allow_html=True)

rows = fetch_access_log()

if not rows:
    st.info("אין כניסות עדיין.")
    st.stop()

# Aggregate per email
df_raw = pd.DataFrame(rows)
df_raw["logged_in_at"] = pd.to_datetime(df_raw["logged_in_at"])

search = st.text_input("🔍 חיפוש לפי אימייל", placeholder="email@...", label_visibility="collapsed")
if search:
    df_raw = df_raw[df_raw["email"].str.contains(search, case=False)]

summary = (
    df_raw.groupby("email")
    .agg(
        first_seen=("logged_in_at", "min"),
        last_seen=("logged_in_at", "max"),
        total_logins=("logged_in_at", "count"),
    )
    .reset_index()
    .sort_values("last_seen", ascending=False)
)

summary["first_seen"] = summary["first_seen"].dt.strftime("%Y-%m-%d %H:%M")
summary["last_seen"]  = summary["last_seen"].dt.strftime("%Y-%m-%d %H:%M")
summary.columns = ["אימייל", "כניסה ראשונה", "כניסה אחרונה", "סה״כ כניסות"]

s1, s2 = st.columns(2)
s1.markdown(f'<div class="stat-card"><div class="stat-num">{len(summary)}</div><div class="stat-label">משתמשים ייחודיים</div></div>', unsafe_allow_html=True)
s2.markdown(f'<div class="stat-card"><div class="stat-num">{len(rows)}</div><div class="stat-label">סה״כ כניסות</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.dataframe(summary, use_container_width=True, hide_index=True)

if st.button("🚪 התנתקות מאדמין"):
    st.session_state.admin_authenticated = False
    st.rerun()
