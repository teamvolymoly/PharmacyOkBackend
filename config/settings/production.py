from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
if not SECRET_KEY or SECRET_KEY.startswith("replace-"):  # noqa: F405
    raise ImproperlyConfigured("Set a strong DJANGO_SECRET_KEY in production.")
if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS cannot be empty in production.")
if not CORS_ALLOWED_ORIGINS:  # noqa: F405
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS cannot be empty in production.")
if PASSWORD_RESET_FIXED_OTP:  # noqa: F405
    raise ImproperlyConfigured("PASSWORD_RESET_FIXED_OTP must never be set in production.")
if ALLOW_DEVELOPMENT_AUTH:  # noqa: F405
    raise ImproperlyConfigured("Development authentication helpers must be disabled in production.")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

