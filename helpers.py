"""
helpers.py — shared X API + AI helpers for Tomer Avital Reply Agent.
"""

from __future__ import annotations
import streamlit as st
import tweepy
import anthropic
import json
import re
import requests
from pathlib import Path

# ── Tomer's fixed config ───────────────────────────────────────────────────────
TOMER_HANDLE   = "TomerAvital1"
TOMER_NAME_HE  = "תומר אביטל"
TOMER_NAME_EN  = "Tomer Avital"
APP_TITLE      = "תומר אביטל · Reply Agent"
APP_ICON       = "🎯"

# ── API clients ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_x_client() -> tweepy.Client:
    return tweepy.Client(
        bearer_token=st.secrets["X_BEARER_TOKEN"],
        consumer_key=st.secrets["X_API_KEY"],
        consumer_secret=st.secrets["X_API_SECRET"],
        access_token=st.secrets["X_ACCESS_TOKEN"],
        access_token_secret=st.secrets["X_ACCESS_SECRET"],
        wait_on_rate_limit=True,
    )

@st.cache_resource
def get_anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


# ── X helpers ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_user_id(handle: str) -> str | None:
    try:
        resp = get_x_client().get_user(username=handle.lstrip("@").strip())
        return str(resp.data.id) if resp.data else None
    except Exception as e:
        st.error(f"לא נמצא @{handle}: {e}")
        return None


@st.cache_data(ttl=7200)
def fetch_tomer_tone_profile() -> str:
    """Fetch Tomer's tweets and build his tone profile."""
    uid = fetch_user_id(TOMER_HANDLE)
    if not uid:
        return ""
    tweets = fetch_client_tweets(uid)
    if not tweets:
        return ""
    return build_tone_profile(tuple(tweets))


@st.cache_data(ttl=7200)
def fetch_client_tweets(user_id: str, max_results: int = 3200) -> list[str]:
    client = get_x_client()
    texts: list[str] = []
    try:
        for page in tweepy.Paginator(
            client.get_users_tweets,
            id=user_id,
            max_results=200,
            tweet_fields=["text"],
            exclude=["retweets", "replies"],
        ).flatten(limit=max_results):
            texts.append(page.text)
    except Exception as e:
        st.warning(f"עצרנו אחרי {len(texts)} ציוצים: {e}")
    return texts


_PREVIEW_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def fetch_link_preview(url: str) -> dict | None:
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=5, headers=_PREVIEW_HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        def og(prop):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            return tag["content"].strip() if tag and tag.get("content") else None

        title = og("og:title") or (soup.title.string.strip() if soup.title else None)
        description = og("og:description")
        image = og("og:image")

        if not title:
            return None
        return {"title": title, "description": description, "image": image, "url": url}
    except Exception:
        return None


def expand_tco_urls(text: str) -> str:
    for url in re.findall(r"https://t\.co/\S+", text):
        try:
            resp = requests.head(url, allow_redirects=True, timeout=3)
            text = text.replace(url, resp.url)
        except Exception:
            pass
    return text


def fetch_target_tweets(user_id: str, count: int = 5) -> list[dict]:
    try:
        resp = get_x_client().get_users_tweets(
            id=user_id,
            max_results=min(count, 100),
            tweet_fields=["text", "created_at"],
            exclude=["retweets"],
        )
        if not resp.data:
            return []
        return [{"id": str(t.id), "text": t.text, "created_at": str(t.created_at)} for t in resp.data]
    except Exception as e:
        st.error(f"שגיאה בטעינת ציוצים: {e}")
        return []


# ── AI helpers ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=7200)
def build_tone_profile(samples: tuple[str, ...]) -> str:
    subset = list(samples[:500])
    joined = "\n---\n".join(subset)
    if len(joined) > 60_000:
        joined = joined[:60_000]

    msg = get_anthropic_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": (
                f"You are analysing {len(subset)} tweets from Tomer Avital (@TomerAvital1), "
                "an Israeli civic entrepreneur, investigative journalist, author, and co-founder of Shakuf and Lobby 99. "
                "He writes primarily in Hebrew and is known for sharp, direct civic commentary.\n\n"
                "Build a detailed ghostwriting profile covering:\n"
                "1. Voice & personality\n"
                "2. Vocabulary and favourite phrases (in Hebrew)\n"
                "3. Sentence structure\n"
                "4. Humour and sarcasm style\n"
                "5. Recurring topics (democracy, transparency, media, politics)\n"
                "6. Emoji usage\n"
                "7. Hashtag usage\n"
                "8. How he engages with others\n"
                "9. Distinctive quirks\n"
                "10. Things to AVOID\n\n"
                "Be very specific — this will be used to write replies indistinguishable from Tomer himself.\n\n"
                f"TWEETS:\n{joined}"
            )
        }]
    )
    return msg.content[0].text


def generate_reply(tweet_text: str, tone_profile: str, author_handle: str) -> str:
    msg = get_anthropic_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                f"You are ghostwriting a reply on X for Tomer Avital (@TomerAvital1), "
                "Israeli civic entrepreneur and investigative journalist.\n\n"
                f"TOMER'S TONE PROFILE:\n{tone_profile}\n\n"
                f"TWEET TO REPLY TO (by @{author_handle}):\n{tweet_text}\n\n"
                "Write ONE reply that:\n"
                "- Sounds exactly like Tomer — match his voice precisely\n"
                "- Is in Hebrew unless the original tweet is in English\n"
                "- Is sharp, direct, and on-brand for a civic journalist\n"
                "- Is under 270 characters\n"
                "- No preamble — reply text only"
            )
        }]
    )
    return msg.content[0].text.strip()


# ── Poller config sync ─────────────────────────────────────────────────────────
def save_poller_config():
    config = {
        "client_handle": TOMER_HANDLE,
        "tone_profile": st.session_state.get("tone_profile", ""),
        "target_accounts": st.session_state.get("target_accounts", []),
    }
    config_path = Path(__file__).parent / "poller_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)



# ── Disk cache paths ───────────────────────────────────────────────────────────
TONE_PROFILE_PATH    = Path(__file__).parent / "tomer_tone_profile.json"
TWEETS_FILE_PATH     = Path(__file__).parent / "tomer_tweets.json"
WATCHED_ACCOUNTS_PATH = Path(__file__).parent / "watched_accounts.json"


def save_watched_accounts(accounts: list[dict]):
    with open(WATCHED_ACCOUNTS_PATH, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)


def load_watched_accounts() -> list[dict]:
    if not WATCHED_ACCOUNTS_PATH.exists():
        return []
    with open(WATCHED_ACCOUNTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_tweets_from_file() -> list[str]:
    path = Path(__file__).parent / "tomer_tweets.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        tweets = data
    else:
        tweets = data.get("tweets", [])
    return [t["text"] if isinstance(t, dict) else t for t in tweets]

def save_tone_profile_to_disk(profile: str, tweet_count: int):
    with open(TONE_PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump({"profile": profile, "tweet_count": tweet_count}, f, ensure_ascii=False)

def load_tone_profile_from_disk() -> dict | None:
    if TONE_PROFILE_PATH.exists():
        with open(TONE_PROFILE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


# ── Shared CSS ─────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700;900&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Heebo', sans-serif;
}

.stApp { background: #0a0a0a; color: #f0f0f0; }

h1, h2, h3 {
    font-family: 'Heebo', sans-serif !important;
    font-weight: 900 !important;
    letter-spacing: -0.02em;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #111111 !important;
    border-right: 1px solid #222;
}
section[data-testid="stSidebar"] * {
    color: #cccccc !important;
}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    background: #1c1c1c !important;
    border-color: #333 !important;
    color: #e0e0e0 !important;
}
section[data-testid="stSidebar"] label {
    color: #cccccc !important;
}
section[data-testid="stSidebar"] a {
    color: #e94560 !important;
}

/* Buttons */
.stButton > button {
    color: #ffffff !important;
}

/* Brand header */
.brand-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border: 1px solid #e94560;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.brand-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #e94560, #f5a623, #e94560);
}
.brand-name-he {
    font-family: 'Heebo', sans-serif;
    font-size: 26px;
    font-weight: 900;
    color: #ffffff;
    direction: rtl;
    margin: 0;
    line-height: 1.2;
}
.brand-name-en {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #e94560;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 4px;
}
.brand-desc {
    font-size: 12px;
    color: #aaaaaa;
    margin-top: 8px;
    direction: rtl;
}

/* Tweet cards */
.tweet-card {
    background: #141414;
    border: 1px solid #222;
    border-left: 3px solid #e94560;
    border-radius: 0 10px 10px 0;
    padding: 18px 20px;
    margin-bottom: 14px;
    transition: border-color 0.2s, transform 0.1s;
}
.tweet-card:hover {
    border-color: #333;
    border-left-color: #f5a623;
}
.tweet-author {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: #e94560;
    margin-bottom: 8px;
    font-weight: 500;
}
.tweet-text {
    font-size: 15px;
    line-height: 1.7;
    color: #f0f0f0;
    direction: rtl;
    text-align: right;
}
.tweet-text-ltr {
    font-size: 15px;
    line-height: 1.7;
    color: #f0f0f0;
}

/* Reply box */
.reply-box {
    background: #0d1f0d;
    border: 1px solid #1a3a1a;
    border-left: 3px solid #22c55e;
    border-radius: 0 8px 8px 0;
    padding: 14px 16px;
    font-size: 14px;
    line-height: 1.7;
    color: #a8ffb0;
    direction: rtl;
    text-align: right;
    margin-bottom: 10px;
}

/* Tone box */
.tone-box {
    background: #0d0d1f;
    border-left: 3px solid #e94560;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 12px;
    color: #aaaaaa;
    font-family: 'DM Mono', monospace;
    direction: rtl;
    text-align: right;
}

/* Status pills */
.status-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-family: 'DM Mono', monospace;
}
.pill-posted    { background: #0d2010; color: #4ade80; border: 1px solid #166534; }
.pill-pending   { background: #1c1700; color: #fbbf24; border: 1px solid #854d0e; }
.pill-failed    { background: #200d0d; color: #f87171; border: 1px solid #991b1b; }
.pill-cancelled { background: #161616; color: #777;    border: 1px solid #333; }
.pill-draft     { background: #0d1520; color: #60a5fa; border: 1px solid #1e3a5f; }

/* Section label */
.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: #888888;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

/* Stat cards */
.stat-card {
    background: #141414;
    border: 1px solid #222;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}
.stat-num   { font-family: 'Heebo', sans-serif; font-size: 30px; font-weight: 900; color: #e94560; }
.stat-label { font-size: 11px; color: #aaaaaa; margin-top: 4px; }

/* Page title */
.page-title {
    font-family: 'Heebo', sans-serif;
    font-size: 36px;
    font-weight: 900;
    color: #ffffff;
    direction: rtl;
    text-align: right;
    border-bottom: 2px solid #e94560;
    padding-bottom: 8px;
    margin-bottom: 24px;
}
.page-title span { color: #e94560; }
</style>
"""
