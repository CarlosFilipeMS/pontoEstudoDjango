from datetime import timedelta
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
TENANTS_DIR = Path(os.getenv("TENANTS_DIR") or str(BASE_DIR / "tenants"))


def _env_or(key: str, default: str) -> str:
    return os.getenv(key) or default

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "companies",
    "core",
    "workforce",
    "attendance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.tenant.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_CATALOG_ENGINE = _env_or(
    "CATALOG_DB_ENGINE",
    _env_or("DB_ENGINE", "django.db.backends.sqlite3"),
)
_CATALOG_NAME = _env_or("CATALOG_DB_NAME", _env_or("DB_NAME", str(BASE_DIR / "catalog.sqlite3")))

DATABASES = {
    "default": {
        "ENGINE": _CATALOG_ENGINE,
        "NAME": _CATALOG_NAME,
        "USER": os.getenv("CATALOG_DB_USER", os.getenv("DB_USER", "")),
        "PASSWORD": os.getenv("CATALOG_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        "HOST": os.getenv("CATALOG_DB_HOST", os.getenv("DB_HOST", "")),
        "PORT": os.getenv("CATALOG_DB_PORT", os.getenv("DB_PORT", "")),
    },
}

TENANT_DATABASE_BASE = {
    "ENGINE": _env_or("TENANT_DB_ENGINE", _env_or("DB_ENGINE", "django.db.backends.sqlite3")),
    "USER": _env_or("TENANT_DB_USER", os.getenv("DB_USER", "")),
    "PASSWORD": _env_or("TENANT_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
    "HOST": _env_or("TENANT_DB_HOST", os.getenv("DB_HOST", "")),
    "PORT": _env_or("TENANT_DB_PORT", os.getenv("DB_PORT", "")),
    "NAME": "",
}

DATABASES["tenant_test"] = {
    **TENANT_DATABASE_BASE,
    "NAME": _env_or("TENANT_TEST_DB_NAME", str(BASE_DIR / "tenant_test.sqlite3")),
}

DATABASE_ROUTERS = ["core.db_router.TenantDatabaseRouter"]

AUTH_USER_MODEL = "workforce.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "core.permissions.IsUsuarioAtivoGlobal",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
}

# Regra de negócio padrão: auto fechamento após 24h.
# Para testes locais, ajuste via env (ex.: 1 minuto).
AUTO_CLOSE_OPEN_ENTRY_MINUTES = int(os.getenv("AUTO_CLOSE_OPEN_ENTRY_MINUTES", "1440"))
