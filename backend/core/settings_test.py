from .settings import *

# Override DATABASES strictly to isolated SQLite in-memory for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Safety check: Ensure tests never accidentally connect to PostgreSQL / Remote host / Supabase
db_engine = DATABASES["default"].get("ENGINE", "")
if "sqlite3" not in db_engine:
    raise RuntimeError(f"TEST SAFETY ERROR: Tests must run on sqlite3, found engine: {db_engine}")

db_host = DATABASES["default"].get("HOST", "")
if db_host:
    raise RuntimeError(f"TEST SAFETY ERROR: Tests must not connect to remote host: {db_host}")
