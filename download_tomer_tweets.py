"""
download_tomer_tweets.py — One-time script to download all of Tomer Avital's tweets.
Saves them to tomer_tweets.json in the project folder.

Run once:
  python download_tomer_tweets.py
"""

import tweepy
import json
import toml
from pathlib import Path
from datetime import datetime

# ── Load secrets ───────────────────────────────────────────────────────────────
SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"
secrets = toml.load(SECRETS_PATH)

client = tweepy.Client(
    bearer_token=secrets["X_BEARER_TOKEN"],
    wait_on_rate_limit=True,
)

HANDLE = "TomerAvital1"
OUTPUT_PATH = Path(__file__).parent / "tomer_tweets.json"

# ── Fetch ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Looking up @{HANDLE}...")
    user = client.get_user(username=HANDLE)
    if not user.data:
        print("User not found.")
        return

    user_id = user.data.id
    print(f"Found: @{HANDLE} (id: {user_id})")
    print("Downloading tweets... (this may take a few minutes)")

    tweets = []
    count = 0

    for tweet in tweepy.Paginator(
        client.get_users_tweets,
        id=user_id,
        max_results=100,
        tweet_fields=["text", "created_at"],
        exclude=["retweets", "replies"],
    ).flatten(limit=3200):
        tweets.append({
            "id": str(tweet.id),
            "text": tweet.text,
            "created_at": str(tweet.created_at),
        })
        count += 1
        if count % 100 == 0:
            print(f"  Downloaded {count} tweets...")

    print(f"\nTotal: {count} tweets downloaded.")

    output = {
        "handle": HANDLE,
        "downloaded_at": datetime.now().isoformat(),
        "tweet_count": count,
        "tweets": tweets,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {OUTPUT_PATH}")
    print("\nDone! You can now load the tone profile from this file — no API needed.")


if __name__ == "__main__":
    main()
