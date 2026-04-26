# Reply Agent

AI-powered tweet reply generator. Reads posts from target accounts and
drafts replies that match your client's tone — then lets you copy or
auto-post them with one click.

## Setup

### 1. X API access
You need **Basic tier** ($100/mo) minimum. This gives you:
- Read access to any public timeline (required for fetching target tweets)
- Write access to post replies

Get credentials at https://developer.x.com/en/portal/dashboard

### 2. Secrets
Copy `secrets.toml.example` → `.streamlit/secrets.toml` and fill in all values.

### 3. Install & run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## How it works

1. **Enter your X handle** in the sidebar → app fetches your last 20 tweets
2. **Claude analyses them** and builds a tone profile (vocabulary, humour level, style, etc.)
3. **Add target accounts** to monitor (e.g. journalists, founders, competitors)
4. **Refresh feed** → fetches their 5 latest tweets each
5. For each tweet, click **✨ Generate reply** → Claude writes a reply in your voice
6. Edit if needed, then **📋 Copy** or **🚀 Post reply**

## Caching
- Tone profile is cached for 1 hour (re-load handle to refresh)
- Target account IDs are cached for 1 hour
- Feed refreshes on demand via the **Refresh feed** button

## Cost estimates (approximate)
- Tone profile build: ~$0.003 per load (20 tweets)
- Reply generation: ~$0.001 per reply
- X API: $100/mo flat (Basic tier)
