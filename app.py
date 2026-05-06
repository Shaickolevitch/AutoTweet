"""
app.py — תומר אביטל · Reply Agent
"""

import streamlit as st
from datetime import datetime

from helpers import (
    GLOBAL_CSS, TOMER_HANDLE, TOMER_NAME_HE, TOMER_NAME_EN, APP_TITLE, APP_ICON,
    fetch_user_id, fetch_target_tweets,
    build_tone_profile, generate_reply, save_poller_config,
    save_tone_profile_to_disk, load_tone_profile_from_disk, load_tweets_from_file,
    expand_tco_urls,
)
from db import log_generated_reply

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in {
    "tone_profile": None,
    "tweet_count": 0,
    "target_accounts": [],
    "feed": {},
    "confirm_refresh": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div class="brand-header">
        <div class="brand-name-he">{TOMER_NAME_HE}</div>
        <div class="brand-name-en">REPLY AGENT · @{TOMER_HANDLE}</div>
        <div class="brand-desc">מערכת תגובות אוטומטית מבוססת AI</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tone profile ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">פרופיל טון</div>', unsafe_allow_html=True)

    # Auto-load from disk on every startup
    if not st.session_state.tone_profile:
        saved = load_tone_profile_from_disk()
        if saved:
            st.session_state.tone_profile = saved["profile"]
            st.session_state.tweet_count  = saved["tweet_count"]

    if st.session_state.tone_profile:
        st.success(f"✅ פרופיל טון טעון ({st.session_state.tweet_count} ציוצים)")
        with st.expander("הצג פרופיל טון"):
            st.markdown(
                f'<div class="tone-box">{st.session_state.tone_profile}</div>',
                unsafe_allow_html=True
            )

        if st.button("🔄 רענן פרופיל", use_container_width=True):
            st.session_state["confirm_refresh"] = True

        if st.session_state.get("confirm_refresh"):
            st.error("⚠️ **פעולה יקרה!**\nטעינת פרופיל טון עולה כ-$20-25.\nהאם אתה בטוח?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ כן, רענן", use_container_width=True):
                    st.session_state["confirm_refresh"] = False
                    st.cache_data.clear()
                    st.session_state.tone_profile = None
                    st.session_state.tweet_count = 0
                    st.rerun()
            with c2:
                if st.button("❌ ביטול", use_container_width=True):
                    st.session_state["confirm_refresh"] = False
                    st.rerun()
    else:
        st.info(f"טוען את פרופיל הכתיבה של @{TOMER_HANDLE} מקובץ...")
        if st.button("📡 טען פרופיל טון", use_container_width=True, type="primary"):
            tweets = load_tweets_from_file()
            if not tweets:
                st.error("לא נמצא tomer_tweets.json או שהקובץ ריק — הרץ את download_tomer_tweets.py קודם")
            else:
                st.session_state.tweet_count = len(tweets)
                with st.spinner(f"מנתח {len(tweets)} ציוצים עם AI..."):
                    st.session_state.tone_profile = build_tone_profile(tuple(tweets))
                save_tone_profile_to_disk(st.session_state.tone_profile, len(tweets))
                save_poller_config()
                st.success(f"✅ פרופיל טון מוכן — {len(tweets)} ציוצים נותחו")
                st.rerun()

    st.markdown("---")

    # ── Target accounts ───────────────────────────────────────────────────────
    st.markdown('<div class="section-label">חשבונות למעקב</div>', unsafe_allow_html=True)
    new_target = st.text_input("הוסף חשבון", placeholder="@someone", label_visibility="collapsed")

    if st.button("➕ הוסף", use_container_width=True):
        t = new_target.lstrip("@").strip()
        existing = [a["handle"] for a in st.session_state.target_accounts]
        if not t:
            st.warning("הכנס שם משתמש")
        elif t in existing:
            st.info(f"@{t} כבר ברשימה")
        else:
            with st.spinner(f"מחפש @{t}..."):
                uid = fetch_user_id(t)
            if uid:
                st.session_state.target_accounts.append({"handle": t, "user_id": uid})
                save_poller_config()
                st.success(f"✅ נוסף @{t}")

    for i, acc in enumerate(st.session_state.target_accounts):
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"<span style='color:#e94560;font-family:monospace'>@{acc['handle']}</span>", unsafe_allow_html=True)
        if c2.button("✕", key=f"rm_{i}"):
            st.session_state.target_accounts.pop(i)
            save_poller_config()
            st.rerun()

    st.markdown("---")
    tweets_per = st.slider("ציוצים לחשבון", 1, 10, 5, help="כמה ציוצים אחרונים לטעון לכל חשבון")

    if st.button("🔄 רענן פיד", use_container_width=True, type="primary"):
        if not st.session_state.target_accounts:
            st.warning("הוסף חשבון קודם")
        elif not st.session_state.tone_profile:
            st.warning("טען פרופיל טון קודם")
        else:
            new_items = {}
            with st.spinner("מוריד ציוצים חדשים..."):
                for acc in st.session_state.target_accounts:
                    for t in fetch_target_tweets(acc["user_id"], count=tweets_per):
                        tid = t["id"]
                        if tid not in st.session_state.feed:
                            new_items[tid] = {**t, "author_handle": acc["handle"], "reply": None}
            st.session_state.feed.update(new_items)
            msg = f"✅ {len(new_items)} ציוצים חדשים" if new_items else "אין ציוצים חדשים"
            st.success(msg) if new_items else st.info(msg)

    st.markdown("---")
    st.page_link("pages/2_📜_History.py", label="📜 היסטוריית תגובות")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Feed
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="page-title">
    📡 פיד ציוצים <span>· {TOMER_NAME_HE}</span>
</div>
""", unsafe_allow_html=True)

if not st.session_state.tone_profile:
    st.info("👈 טען את פרופיל הטון של תומר מהסייד-בר כדי להתחיל")
    st.stop()

if not st.session_state.target_accounts:
    st.info("👈 הוסף חשבונות למעקב ולחץ **רענן פיד**")
    st.stop()

if not st.session_state.feed:
    st.info("לחץ **רענן פיד** בסייד-בר לטעינת ציוצים")
    st.stop()

sorted_feed = sorted(
    st.session_state.feed.items(),
    key=lambda x: x[1].get("created_at", ""),
    reverse=True,
)

for tweet_id, item in sorted_feed:
    date_str = item.get("created_at", "")[:10]
    display_text = expand_tco_urls(item["text"])
    is_hebrew = any("֐" <= c <= "׿" for c in display_text)
    text_class = "tweet-text" if is_hebrew else "tweet-text-ltr"

    st.markdown(f"""
    <div class="tweet-card">
        <div class="tweet-author">@{item['author_handle']} · {date_str}</div>
        <div class="{text_class}">{display_text}</div>
    </div>
    """, unsafe_allow_html=True)

    col_gen, _ = st.columns([2, 5])
    with col_gen:
        if st.button("✨ צור תגובה", key=f"gen_{tweet_id}"):
            with st.spinner("כותב תגובה בסגנון תומר..."):
                reply = generate_reply(
                    tweet_text=item["text"],
                    tone_profile=st.session_state.tone_profile,
                    author_handle=item["author_handle"],
                )
            st.session_state.feed[tweet_id]["reply"] = reply
            log_generated_reply(
                client_handle=TOMER_HANDLE,
                tweet_id=tweet_id,
                author_handle=item["author_handle"],
                original_text=item["text"],
                reply_text=reply,
            )
            st.rerun()

    if item.get("reply"):
        reply_text = item["reply"]
        char_count = len(reply_text)
        color = "#4ade80" if char_count <= 270 else "#f87171"

        st.markdown(f'<div class="reply-box">{reply_text}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<span style="font-size:11px;color:{color};font-family:monospace">{char_count}/270 תווים</span>',
            unsafe_allow_html=True,
        )

        edited = st.text_area(
            "ערוך", value=reply_text, key=f"edit_{tweet_id}",
            height=80, label_visibility="collapsed",
        )
        st.session_state.feed[tweet_id]["reply"] = edited

        col_copy, col_regen = st.columns([2, 2])

        with col_copy:
            st.markdown(
                f"""<button onclick="navigator.clipboard.writeText({repr(edited)});
                    this.innerText='✅ הועתק!';setTimeout(()=>this.innerText='📋 העתק',1500)"
                    style="width:100%;padding:8px 0;background:#141414;border:1px solid #333;
                           border-radius:6px;color:#e0e0e0;cursor:pointer;font-size:13px;
                           font-family:Heebo,sans-serif;">
                    📋 העתק
                </button>""",
                unsafe_allow_html=True,
            )

        with col_regen:
            if st.button("🔁 כתוב מחדש", key=f"regen_{tweet_id}"):
                with st.spinner("כותב מחדש..."):
                    new_reply = generate_reply(
                        tweet_text=item["text"],
                        tone_profile=st.session_state.tone_profile,
                        author_handle=item["author_handle"],
                    )
                st.session_state.feed[tweet_id]["reply"] = new_reply
                log_generated_reply(
                    client_handle=TOMER_HANDLE,
                    tweet_id=tweet_id,
                    author_handle=item["author_handle"],
                    original_text=item["text"],
                    reply_text=new_reply,
                )
                st.rerun()

    st.markdown("---")
