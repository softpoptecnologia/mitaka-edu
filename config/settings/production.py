"""Production settings."""
from .base import *  # noqa: F401,F403

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
USE_X_FORWARDED_HOST = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CELERY_TASK_ALWAYS_EAGER = False

CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys(
        CSRF_TRUSTED_ORIGINS
        + env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=["https://edu.innomove.com.br"])
        + csrf_origins_from_hosts(ALLOWED_HOSTS)
        + ["https://edu.innomove.com.br", "https://www.edu.innomove.com.br"]
    )
)
