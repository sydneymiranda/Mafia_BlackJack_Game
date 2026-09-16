# Security notes

What's in place, and why.

## Passwords
- Never stored in plaintext. Hashed with PBKDF2-HMAC-SHA256, 210,000
  iterations, a unique random 16-byte salt per account.
- Signup requires 8+ characters and a valid-looking email format.
- Login attempts are rate-limited: 5 wrong passwords locks that account
  for 5 minutes (tracked per-account in MongoDB, not just client-side —
  editing local files can't bypass it).

## Local session files
- `session.json` remembers who's logged in between launches, but it's
  HMAC-SHA256 signed with a locally-generated secret (`.session_secret`,
  gitignored, never shared). Hand-editing the file to swap in a different
  `user_id` fails the signature check and the session is discarded rather
  than trusted.
- `token.json` (Google OAuth token) and `credentials.json` (your Google
  Cloud OAuth client) are both gitignored — never commit either.

## Secrets & config
- MongoDB connection string comes from an environment variable
  (`MONGO_URI`, via `.env`), not hardcoded — `.env` is gitignored.
  `.env.example` shows the shape without real values.
- If you ever move MongoDB off localhost, also enable MongoDB's own
  authentication (username/password) and put the credentials in `.env`
  rather than the connection string in code.

## What's intentionally out of scope for now
- This is a local single-player desktop app — there's no network-facing
  server for someone to attack remotely. The threat model here is mainly
  "someone else using the same PC," which is what the signed sessions and
  gitignored secrets address.
- If this ever becomes networked (a real backend, multiplayer, etc.),
  revisit: TLS for any network calls, server-side session tokens instead
  of local files, and moving MongoDB behind real authentication + network
  restrictions.
