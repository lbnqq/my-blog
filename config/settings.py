from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent.parent

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")


def split_env_list(name, default=""):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = env_flag("DEBUG", True)
ALLOWED_HOSTS = split_env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = split_env_list("CSRF_TRUSTED_ORIGINS")
ALLOW_LAN_ACCESS = env_flag("ALLOW_LAN_ACCESS")
if DEBUG and ALLOW_LAN_ACCESS and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.agent",
    "apps.accounts",
    "apps.blog",
    "apps.movies",
    "apps.ratings",
    "apps.recommendations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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


USE_SQLITE = os.getenv("USE_SQLITE", "").lower() in {"1", "true", "yes", "on"}

if os.getenv("SUPABASE_DB_HOST") and not USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("SUPABASE_DB_NAME", "postgres"),
            "USER": os.getenv("SUPABASE_DB_USER", "postgres"),
            "PASSWORD": os.getenv("SUPABASE_DB_PASSWORD"),
            "HOST": os.getenv("SUPABASE_DB_HOST"),
            "PORT": os.getenv("SUPABASE_DB_PORT", "5432"),
            "OPTIONS": {
                "sslmode": os.getenv("SUPABASE_DB_SSLMODE", "require"),
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
LANGUAGES = [
    ("zh-hans", "中文"),
    ("en", "English"),
]
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
if not DEBUG:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "blog:home"
LOGOUT_REDIRECT_URL = "blog:home"
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-5.1")
ZHIPU_API_URL = os.getenv(
    "ZHIPU_API_URL",
    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
)
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
FEISHU_ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "")
SITE_PUBLIC_URL = os.getenv("SITE_PUBLIC_URL", "")
