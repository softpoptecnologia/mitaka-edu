"""Local development settings."""
from .base import *  # noqa: F401,F403

DEBUG = True
CELERY_TASK_ALWAYS_EAGER = True
ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + ["localhost", "127.0.0.1", "testserver", "web"]))

# Prefer simple static serving in local without requiring collectstatic hashes
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
