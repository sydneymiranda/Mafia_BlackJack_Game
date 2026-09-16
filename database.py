"""
MongoDB data layer.
Assumes a local MongoDB server (default: mongodb://localhost:27017).
No cloud service used — swap MONGO_URI later if you move to Atlas.
"""

import hashlib
import os
import uuid
from datetime import datetime, timedelta

from pymongo import MongoClient

import constants as C
import config

MONGO_URI = config.MONGO_URI
DB_NAME = "mafia_blackjack"
GUEST_VALID_DAYS = 30
STARTING_BALANCE = 500
PBKDF2_ITERATIONS = 210_000  # OWASP-recommended ballpark for PBKDF2-HMAC-SHA256
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 5

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    return get_client()[DB_NAME]


def get_users():
    return get_db()["users"]


def check_connection():
    """Raises if MongoDB isn't reachable — call this early so failures are clear."""
    get_client().admin.command("ping")


def _default_run_fields():
    """Loan/shop state every new account starts with."""
    return {
        "loan_level": 1,
        "target": C.BASE_LOAN_TARGET,
        "rounds_left": C.BASE_LOAN_ROUNDS,
        "inventory": {},
    }


# ----- Google users -----

def upsert_google_user(sub, email, name):
    """sub = Google's stable user id (from the ID token)."""
    users = get_users()
    user_id = f"google_{sub}"
    existing = users.find_one({"_id": user_id})
    if existing:
        users.update_one({"_id": user_id}, {"$set": {"email": email, "name": name}})
        return user_id

    users.insert_one({
        "_id": user_id,
        "auth_type": "google",
        "email": email,
        "name": name,
        "created_at": datetime.utcnow(),
        "expires_at": None,
        "balance": STARTING_BALANCE,
        **_default_run_fields(),
    })
    return user_id


# ----- Guest users -----

def create_guest_user():
    users = get_users()
    user_id = f"guest_{uuid.uuid4().hex[:12]}"
    expires_at = datetime.utcnow() + timedelta(days=GUEST_VALID_DAYS)
    users.insert_one({
        "_id": user_id,
        "auth_type": "guest",
        "email": None,
        "name": "Guest",
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "balance": STARTING_BALANCE,
        **_default_run_fields(),
    })
    return user_id, expires_at


# ----- Shared -----

def get_user(user_id):
    return get_users().find_one({"_id": user_id})


def is_session_valid(user_id):
    user = get_user(user_id)
    if not user:
        return False
    if user["auth_type"] == "guest":
        return user["expires_at"] is not None and user["expires_at"] > datetime.utcnow()
    return True  # google sessions don't expire on our side


def get_balance(user_id):
    user = get_user(user_id)
    return user["balance"] if user else STARTING_BALANCE


def set_balance(user_id, balance):
    get_users().update_one({"_id": user_id}, {"$set": {"balance": balance}})


def delete_user(user_id):
    get_users().delete_one({"_id": user_id})


# ----- Local email/password accounts -----

def _hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt, digest


def create_local_user(email, name, password):
    """Returns None if that email is already registered as a local account."""
    email = email.strip().lower()
    users = get_users()
    if users.find_one({"email": email, "auth_type": "local"}):
        return None

    salt, digest = _hash_password(password)
    user_id = f"local_{uuid.uuid4().hex[:12]}"
    users.insert_one({
        "_id": user_id,
        "auth_type": "local",
        "email": email,
        "name": name,
        "password_salt": salt.hex(),
        "password_hash": digest.hex(),
        "failed_attempts": 0,
        "locked_until": None,
        "created_at": datetime.utcnow(),
        "expires_at": None,
        "balance": STARTING_BALANCE,
        **_default_run_fields(),
    })
    return user_id


def verify_local_login(email, password):
    """Returns (user_id, None) on success, or (None, error_message) on
    failure — including a message when the account is temporarily locked."""
    email = email.strip().lower()
    users = get_users()
    user = users.find_one({"email": email, "auth_type": "local"})
    if not user:
        return None, "Incorrect email or password."

    locked_until = user.get("locked_until")
    if locked_until and locked_until > datetime.utcnow():
        remaining = max(1, int((locked_until - datetime.utcnow()).total_seconds() // 60) + 1)
        return None, f"Too many failed attempts. Try again in {remaining} minute(s)."

    salt = bytes.fromhex(user["password_salt"])
    _, digest = _hash_password(password, salt)

    if digest.hex() == user["password_hash"]:
        users.update_one({"_id": user["_id"]}, {"$set": {"failed_attempts": 0, "locked_until": None}})
        return user["_id"], None

    attempts = user.get("failed_attempts", 0) + 1
    update = {"failed_attempts": attempts}
    if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        update["locked_until"] = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        message = f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes."
    else:
        message = "Incorrect email or password."
    users.update_one({"_id": user["_id"]}, {"$set": update})
    return None, message


# ----- Loan / boss progress -----

def ensure_loan_fields(user_id):
    """Backfills loan/inventory fields for accounts created before this
    feature existed. Returns the (possibly updated) user document."""
    user = get_user(user_id)
    if user is None:
        return None
    defaults = _default_run_fields()
    missing = {k: v for k, v in defaults.items() if k not in user}
    if missing:
        get_users().update_one({"_id": user_id}, {"$set": missing})
        user.update(missing)
    return user


def get_loan_state(user_id):
    user = ensure_loan_fields(user_id)
    return {
        "loan_level": user["loan_level"],
        "target": user["target"],
        "rounds_left": user["rounds_left"],
    }


def set_loan_state(user_id, loan_level, target, rounds_left):
    get_users().update_one({"_id": user_id}, {"$set": {
        "loan_level": loan_level,
        "target": target,
        "rounds_left": rounds_left,
    }})


def reset_run(user_id):
    """Called when the player fails to hit the target in time — the boss
    resets everything back to the start."""
    defaults = _default_run_fields()
    get_users().update_one({"_id": user_id}, {"$set": {
        "balance": STARTING_BALANCE,
        **defaults,
    }})


def get_inventory(user_id):
    return ensure_loan_fields(user_id)["inventory"]


def add_item(user_id, item_id, qty=1):
    get_users().update_one({"_id": user_id}, {"$inc": {f"inventory.{item_id}": qty}})


def use_item(user_id, item_id):
    """Decrements the item count by 1 if the player has any. Returns True if used."""
    inventory = get_inventory(user_id)
    if inventory.get(item_id, 0) <= 0:
        return False
    get_users().update_one({"_id": user_id}, {"$inc": {f"inventory.{item_id}": -1}})
    return True
