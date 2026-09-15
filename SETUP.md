# Setup: Google Sign-In + MongoDB

## 1. Install dependencies

```
pip install -r requirements.txt
```

## 2. MongoDB (local, no cloud)

Install MongoDB Community Server and make sure it's running as a local
service (default port 27017). The app connects to `mongodb://localhost:27017`
and creates the `mafia_blackjack` database automatically on first use —
no manual schema setup needed.

Check it's running:
```
mongosh
```
If that connects, you're good.

## 3. Google OAuth credentials (one-time)

1. Go to https://console.cloud.google.com/ and create a project (or use an existing one).
2. APIs & Services > OAuth consent screen — set it up as "External", add your own
   Gmail as a test user (this keeps it free and avoids Google's app review).
3. APIs & Services > Credentials > Create Credentials > OAuth client ID.
4. Application type: **Desktop app**. Name it anything (e.g. "Mafia Blackjack").
5. Download the JSON, rename it to `credentials.json`, and place it in the
   `blackjack_game` folder (same level as `main.py`).

`credentials.json` is your app's identity, not a user secret, but keep it out
of git anyway (already in `.gitignore`).

## Files created at runtime (all gitignored)

- `token.json` — cached Google OAuth token, so you're not re-approving every launch
- `session.json` — remembers whether you last signed in as guest or Google
