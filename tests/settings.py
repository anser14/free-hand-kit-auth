"""Minimal Django settings used only by the package test suite."""

from __future__ import annotations

SECRET_KEY = "test-only-django-secret-key"
DEBUG = False
USE_TZ = True
ROOT_URLCONF = "fk_auth.urls"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "tests.test_app",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "fk_auth",
]
AUTH_USER_MODEL = "fk_auth_test_app.CustomUser"
MIDDLEWARE: list[str] = []
ALLOWED_HOSTS = ["testserver"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

FREEHAND_KIT_AUTH = {
    "JWT": {
        "SIGNING_KEY": "test-only-jwt-signing-key-that-is-not-a-real-secret",
    }
}
