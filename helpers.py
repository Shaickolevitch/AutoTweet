"""
helpers.py — shared X API + AI helpers for Reply Agent.
"""

from __future__ import annotations
import streamlit as st
import tweepy
import anthropic


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
        st.error(f"Could not find @{handle}: {e}")
        return None


@st.cache_data(ttl=3600)
def fetch_client_tweets(user_id: str, max_pages: int = 16) -> list[str]:
    """
    Fetch up to 3,200 of the client's own tweets for tone analysis.
    Tweepy's Paginator handles pagination automatically.
    max_pages × 200 tweets = up to 3,200 (API max).
    """
    client = get_x_client()
    texts: list[str] = []
    try:
        for page in tweepy.Paginator(
            client.get_users_tweets,
            id=user_id,
            max_results=200,
            tweet_fields=["text"],
            exclude=["retweets", "replies"],
        ).flatten(limit=3200):
            texts.append(page.text)
    except Exception as e:
        st.warning(f"Stopped fetching at {len(texts)} tweets: {e}")
    return texts


def fetch_target_tweets(user_id: str, count: int = 5) -> list[dict]:
    try:
        resp = get_x_client().get_users_tweets(
            id=user_id,
            max_results=min(max(count, 5), 100),
            tweet_fields=["text", "created_at"],
            exclude=["retweets"],
        )
        if not resp.data:
            return []
        return [{"id": str(t.id), "text": t.text, "created_at": str(t.created_at)} for t in resp.data]
    except Exception as e:
        st.error(f"Error fetching target tweets: {e}")
        return []


def post_reply(tweet_id: str, reply_text: str) -> bool:
    try:
        get_x_client().create_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
        return True
    except Exception as e:
        st.error(f"Failed to post reply: {e}")
        return False


# ── AI helpers ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=7200)
def build_tone_profile(samples: tuple[str, ...]) -> str:
    """
    Build a detailed tone profile from up to 3,200 sample tweets.
    Sends up to 500 tweets (to stay within token limits) for analysis.
    """
    # Use up to 500 of the most recent tweets, trimmed to ~60k chars total
    subset = list(samples[:500])
    joined = "\n---\n".join(subset)
    if len(joined) > 60_000:
        joined = joined[:60_000]

    msg = get_anthropic_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": (
                f"You are analysing {len(subset)} tweets from a single person to build a detailed ghostwriting profile.\n\n"
                "Return a structured tone profile covering ALL of the following:\n"
                "1. Voice & personality (formal/casual, confident/humble, etc.)\n"
                "2. Vocabulary level and favourite words/phrases\n"
                "3. Sentence structure (short punchy vs. long detailed)\n"
                "4. Humour style (dry, sarcastic, none, self-deprecating, etc.)\n"
                "5. Recurring topics and themes\n"
                "6. Emoji usage (none / occasional / heavy)\n"
                "7. Hashtag usage\n"
                "8. How they engage with others (supportive, challenging, neutral)\n"
                "9. Any distinctive quirks or patterns\n"
                "10. Things to AVOID (patterns that would break the voice)\n\n"
                "Be specific and concrete. This profile will be used to write replies that are indistinguishable from the real person.\n\n"
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
                "You are ghostwriting a reply on X (Twitter) for a client.\n\n"
                f"CLIENT TONE PROFILE:\n{tone_profile}\n\n"
                f"TWEET TO REPLY TO (by @{author_handle}):\n{tweet_text}\n\n"
                "Write ONE reply that:\n"
                "- Sounds exactly like the client — match their voice precisely\n"
                "- Is relevant, adds value, or sparks engagement\n"
                "- Is under 270 characters (leave buffer)\n"
                "- Follows the client's emoji and hashtag habits\n"
                "- No quotes, no preamble — reply text only"
            )
        }]
    )
    return msg.content[0].text.strip()


# ── Shared CSS ─────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0d0d0d; color: #e8e8e8; }
h1, h2, h3 { font-family: 'DM Mono', monospace !important; letter-spacing: -0.03em; }

.tweet-card {
    background: #161616; border: 1px solid #2a2a2a;
    border-radius: 12px; padding: 20px; margin-bottom: 16px;
}
.tweet-card:hover { border-color: #444; }
.tweet-author { font-family: 'DM Mono', monospace; font-size: 13px; color: #888; margin-bottom: 8px; }
.tweet-text { font-size: 15px; line-height: 1.6; color: #e0e0e0; margin-bottom: 4px; }
.reply-box {
    background: #1a2a1a; border: 1px solid #2d4a2d;
    border-radius: 8px; padding: 14px; font-size: 14px;
    line-height: 1.6; color: #c8f0c8; margin-bottom: 10px;
}
.tone-box {
    background: #111; border-left: 3px solid #4a9eff;
    padding: 12px 16px; border-radius: 0 8px 8px 0;
    font-size: 13px; color: #aaa; font-family: 'DM Mono', monospace;
}
.status-pill {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-family: 'DM Mono', monospace;
}
.pill-posted  { background: #1a2a1a; color: #5db85d; border: 1px solid #2d4a2d; }
.pill-pending { background: #2a2a1a; color: #c8b84a; border: 1px solid #4a4a2d; }
.pill-failed  { background: #2a1a1a; color: #c85d5d; border: 1px solid #4a2d2d; }
.pill-cancelled { background: #1e1e1e; color: #777; border: 1px solid #333; }
.section-label {
    font-family: 'DM Mono', monospace; font-size: 11px; color: #555;
    letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 8px;
}
.stat-card {
    background: #161616; border: 1px solid #2a2a2a; border-radius: 10px;
    padding: 16px; text-align: center;
}
.stat-num { font-family: 'DM Mono', monospace; font-size: 28px; color: #4a9eff; }
.stat-label { font-size: 12px; color: #666; margin-top: 4px; }
</style>
"""
