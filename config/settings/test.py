import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-with-at-least-32-bytes")
os.environ.setdefault("DJANGO_DEBUG", "False")
os.environ.setdefault("POSTGRES_DB", "unused")
os.environ.setdefault("POSTGRES_USER", "unused")
os.environ.setdefault("POSTGRES_PASSWORD", "unused")

from .base import *  # noqa: E402,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PASSWORD_RESET_FIXED_OTP = "4562"
ALLOW_DEVELOPMENT_AUTH = True
