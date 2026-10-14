import os

os.environ.setdefault("DJANGO_SECRET_KEY", "local-development-secret-key-change-before-production")
os.environ.setdefault("DJANGO_DEBUG", "True")
os.environ.setdefault("POSTGRES_DB", "unused")
os.environ.setdefault("POSTGRES_USER", "unused")
os.environ.setdefault("POSTGRES_PASSWORD", "unused")

from .development import *  # noqa: E402,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}
