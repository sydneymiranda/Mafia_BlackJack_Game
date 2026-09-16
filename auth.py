"""
Google sign-in via the standard "installed app" OAuth flow: opens the
user's browser, they approve, a local throwaway server on localhost
catches the redirect. No cloud backend involved — Google's own OAuth
servers are the only external call.

Setup required (one-time, see SETUP.md):
    pip install google-auth google-auth-oauthlib
    Download an OAuth "Desktop app" client from Google Cloud Console
    and save it next to this file as credentials.json

token.json / session.json are local cache files (gitignored) so the
player isn't forced to re-approve or re-pick guest/google every launch.
session.json is HMAC-signed (see _sign) so editing it by hand to swap
in a different user_id is detected and rejected rather than silently
letting someone hijack another local account.
"""

import hashlib
import hmac
import json
import os
import re
import secrets

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import requests

import database

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
SESSION_FILE = "session.json"
SECRET_KEY_FILE = ".session_secret"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


class AuthError(Exception):
    pass


# ----- input validation -----

def _validate_email(email):
    if not email or not EMAIL_PATTERN.match(email):
        raise AuthError("Enter a valid email address.")


def _validate_password_strength(password):
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


# ----- Google OAuth -----

def _fetch_userinfo(creds):
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["id"], data.get("email"), data.get("name", "Player")


def google_sign_in():
    """Runs the full browser-popup flow. Returns a user_id."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise AuthError(
            f"{CREDENTIALS_FILE} not found. See SETUP.md to create Google OAuth credentials."
        )
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    sub, email, name = _fetch_userinfo(creds)
    user_id = database.upsert_google_user(sub, email, name)
    _save_session({"auth_type": "google", "user_id": user_id})
    return user_id


def _try_refresh_google_session():
    """Silent re-login using the cached token, if we have one and it still works."""
    if not os.path.exists(TOKEN_FILE):
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            return creds
        except Exception:
            return None
    return None


# ----- Local email/password accounts -----

def local_sign_up(email, name, password):
    email = email.strip().lower()
    _validate_email(email)
    _validate_password_strength(password)

    user_id = database.create_local_user(email, name, password)
    if user_id is None:
        raise AuthError("An account with that email already exists.")
    _save_session({"auth_type": "local", "user_id": user_id})
    return user_id


def local_sign_in(email, password):
    email = email.strip().lower()
    _validate_email(email)

    user_id, error = database.verify_local_login(email, password)
    if user_id is None:
        raise AuthError(error or "Incorrect email or password.")
    _save_session({"auth_type": "local", "user_id": user_id})
    return user_id


# ----- Guest -----

def create_guest():
    user_id, expires_at = database.create_guest_user()
    _save_session({"auth_type": "guest", "user_id": user_id})
    return user_id, expires_at


# ----- Session persistence (HMAC-signed, tamper-evident) -----

def _get_or_create_secret():
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE) as f:
            return bytes.fromhex(f.read().strip())
    key = secrets.token_bytes(32)
    with open(SECRET_KEY_FILE, "w") as f:
        f.write(key.hex())
    return key


_SECRET_KEY = _get_or_create_secret()


def _sign(payload):
    return hmac.new(_SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _save_session(data):
    payload = json.dumps(data, sort_keys=True)
    with open(SESSION_FILE, "w") as f:
        json.dump({"data": data, "sig": _sign(payload)}, f)


def clear_session():
    """Used by the 'sign out / back' option — forces the login screen next time."""
    for f in (SESSION_FILE, TOKEN_FILE):
        if os.path.exists(f):
            os.remove(f)


def delete_account(user_id):
    """Removes the account/guest record entirely and clears the local session."""
    database.delete_user(user_id)
    clear_session()


def load_saved_session():
    """Returns a user_id if a still-valid, untampered session exists locally,
    else None. A session.json that's been hand-edited fails the signature
    check and is discarded rather than trusted."""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE) as f:
            envelope = json.load(f)
        data = envelope["data"]
        sig = envelope["sig"]
    except (json.JSONDecodeError, OSError, KeyError):
        return None

    expected_sig = _sign(json.dumps(data, sort_keys=True))
    if not hmac.compare_digest(sig, expected_sig):
        clear_session()  # tampered or corrupted — don't trust it
        return None

    user_id = data.get("user_id")
    auth_type = data.get("auth_type")
    if not user_id or not auth_type:
        return None

    if not database.is_session_valid(user_id):
        return None  # guest expired, or user no longer exists

    if auth_type == "google":
        creds = _try_refresh_google_session()
        if creds is None:
            return None

    return user_id
