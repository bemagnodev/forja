"""Run only on loopback, against an explicit disposable SQLite copy."""
import os
from pathlib import Path
from core.settings import *  # noqa: F403

VISUAL_PREVIEW = True
VISUAL_PREVIEW_ROOT = (BASE_DIR / 'var' / 'visual-review').resolve()  # noqa: F405
preview_path = Path(os.environ.get('VISUAL_PREVIEW_DB', '')).resolve()
if not os.environ.get('VISUAL_PREVIEW_DB') or not preview_path.is_relative_to(VISUAL_PREVIEW_ROOT):
    raise ValueError('VISUAL_PREVIEW_DB must explicitly name a file inside backend/var/visual-review')
if preview_path.suffix != '.sqlite3':
    raise ValueError('VISUAL_PREVIEW_DB must be a SQLite file')
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': preview_path}}
SECRET_KEY = 'forja-disposable-local-preview-only'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '[::1]']
CORS_ALLOWED_ORIGINS = ['http://127.0.0.1:5173', 'http://localhost:5173']
CORS_ALLOW_ALL_ORIGINS = False
FRONTEND_URL = 'http://127.0.0.1:5173'
MIDDLEWARE = ['api.visual_preview.PreviewNetworkGuard', *MIDDLEWARE]  # noqa: F405
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
AI_LAB_USE_PRIVATE_RESULTS = False
