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

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "mafia_blackjack"
GUEST_VALID_DAYS = 30
STARTING_BALANCE = 500

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
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt, digest


def create_local_user(email, name, password):
    """Returns None if that email is already registered as a local account."""
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
        "created_at": datetime.utcnow(),
        "expires_at": None,
        "balance": STARTING_BALANCE,
    })
    return user_id


def verify_local_login(email, password):
    """Returns the user_id on success, None on bad email/password."""
    user = get_users().find_one({"email": email, "auth_type": "local"})
    if not user:
        return None
    salt = bytes.fromhex(user["password_salt"])
    _, digest = _hash_password(password, salt)
    if digest.hex() == user["password_hash"]:
        return user["_id"]
    return None