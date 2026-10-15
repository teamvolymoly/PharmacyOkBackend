import os

# Base settings ko import karne ke liye
# PostgreSQL placeholders
os.environ.setdefault("POSTGRES_DB", "unused")
os.environ.setdefault("POSTGRES_USER", "unused")
os.environ.setdefault("POSTGRES_PASSWORD", "unused")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Existing production security settings
from .production import *  # noqa: F403

# Render free testing ke liye SQLite
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
