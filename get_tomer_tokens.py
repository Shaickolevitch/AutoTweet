"""
get_tomer_tokens.py — One-time OAuth 1.0a authorization script.
Run this once to get Tomer's Access Token + Secret.

Usage:
  python get_tomer_tokens.py
"""

import tweepy
import webbrowser

# ── Paste your app's Consumer Key and Secret here ─────────────────────────────
API_KEY    = "1BDc8sOscfni6kWyxUHz3uXdC"
API_SECRET = "19DlGDIuAbdachxuHF6qOzEcENSmSr3MsJIfpDTfsn0W2C6NYr"
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n🔑 Reply Agent — Tomer Avital Token Authorization")
    print("=" * 50)

    auth = tweepy.OAuth1UserHandler(
        API_KEY, API_SECRET,
        callback="oob"  # Out-of-band (PIN-based) — no server needed
    )

    try:
        redirect_url = auth.get_authorization_url()
    except tweepy.TweepyException as e:
        print(f"\n❌ Error: {e}")
        print("Make sure your Consumer Key and Secret are correct.")
        return

    print("\n📋 Step 1: Open this URL in Tomer's browser (or send it to him):")
    print(f"\n  {redirect_url}\n")

    # Try to open automatically
    try:
        webbrowser.open(redirect_url)
        print("  (Opened automatically in your browser)")
    except:
        print("  (Copy and open manually)")

    print("\n📋 Step 2: Tomer logs in with @TomerAvital1 and clicks Authorize")
    print("📋 Step 3: X will show a PIN code — enter it below\n")

    pin = input("Enter the PIN from X: ").strip()

    try:
        auth.get_access_token(pin)
        access_token        = auth.access_token
        access_token_secret = auth.access_token_secret

        print("\n" + "=" * 50)
        print("✅ SUCCESS! Add these to your .streamlit/secrets.toml:")
        print("=" * 50)
        print(f'\nX_ACCESS_TOKEN    = "{access_token}"')
        print(f'X_ACCESS_SECRET   = "{access_token_secret}"')
        print("\n" + "=" * 50)
        print("These tokens are for @TomerAvital1 — keep them secret!")

    except tweepy.TweepyException as e:
        print(f"\n❌ Error getting access token: {e}")
        print("Make sure you entered the PIN correctly.")


if __name__ == "__main__":
    main()
