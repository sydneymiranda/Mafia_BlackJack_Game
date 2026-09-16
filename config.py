"""
Central configuration. Values come from environment variables (or a local
.env file) instead of being hardcoded — so nothing secret ends up in git,
and swapping to a remote MongoDB later is a one-line change, not a code
change.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # loads .env if present; harmless no-op if it isn't

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
