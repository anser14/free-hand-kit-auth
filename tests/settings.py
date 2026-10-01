"""Minimal Django settings used only by the package test suite."""

from __future__ import annotations

import os

SECRET_KEY = "test-only-django-secret-key"
DEBUG = False
USE_TZ = True
ROOT_URLCONF = "fk_auth.urls"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
if os.environ.get("FK_AUTH_TEST_POSTGRES"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "fk_auth_test"),
            "USER": os.environ.get("POSTGRES_USER", "fk_auth"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "fk_auth"),
            "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
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
if os.environ.get("FK_AUTH_TEST_SMTP"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "127.0.0.1")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
    EMAIL_USE_TLS = False
    EMAIL_USE_SSL = False
if redis_url := os.environ.get("FK_AUTH_TEST_REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_url,
        }
    }
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

FREEHAND_KIT_AUTH = {
    "JWT": {
        "SIGNING_KEY": "test-only-jwt-signing-key-that-is-not-a-real-secret",
    },
    "THROTTLE": {"REQUIRE_SHARED_CACHE": False},
}
