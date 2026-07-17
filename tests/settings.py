"""Minimal settings for the test suite."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "not-a-secret"  # noqa: S105
DEBUG = True
USE_TZ = True

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # TemplatesSetting resolves widget templates through the project's engine, so
    # Django's own widget templates need to be discoverable via APP_DIRS.
    "django.forms",
    "widget_renderers",  # AppConfig.ready() calls install()
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# TemplatesSetting makes widget templates resolve through the project's template
# dirs, which is what lets a renderer point at its own templates.
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

STATIC_URL = "/static/"
ROOT_URLCONF = "tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
