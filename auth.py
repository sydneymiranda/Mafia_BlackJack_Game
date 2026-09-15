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
"""

import json
import os

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


class AuthError(Exception):
    pass


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
    user_id = database.create_local_user(email, name, password)
    if user_id is None:
        raise AuthError("An account with that email already exists.")
    _save_session({"auth_type": "local", "user_id": user_id})
    return user_id


def local_sign_in(email, password):
    user_id = database.verify_local_login(email, password)
    if user_id is None:
        raise AuthError("Incorrect email or password.")
    _save_session({"auth_type": "local", "user_id": user_id})
    return user_id


# ----- Guest -----

def create_guest():
    user_id, expires_at = database.create_guest_user()
    _save_session({"auth_type": "guest", "user_id": user_id})
    return user_id, expires_at


# ----- Session persistence -----

def _save_session(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)


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
    """Returns a user_id if a still-valid session exists locally, else None."""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
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