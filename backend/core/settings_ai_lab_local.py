"""Explicit local operations; never use this configuration for pytest."""
import os
from pathlib import Path

if not os.environ.get("AI_LAB_SQLITE_PATH"):
    raise ValueError("AI_LAB_SQLITE_PATH must explicitly name a local SQLite file")

from core.settings import *  # noqa: F403,E402
from api.ai_lab.runner import require_local_environment  # noqa: E402

AI_LAB_ROOT = (BASE_DIR / "var" / "ai_lab").resolve()  # noqa: F405
AI_LAB_USE_PRIVATE_RESULTS = True
# Override inherited database configuration before Django can open any connection.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ["AI_LAB_SQLITE_PATH"]}}
require_local_environment("core.settings_ai_lab_local", DATABASES["default"], AI_LAB_ROOT)
