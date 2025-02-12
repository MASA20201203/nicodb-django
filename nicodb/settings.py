"""
Django settings for nicodb project.

Generated by 'django-admin startproject' using Django 5.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
import socket
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("ERROR: SECRET_KEY is not set in the environment variables.")


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS: list[str] = os.getenv("ALLOWED_HOSTS", "").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party apps
    "axes",  # 管理画面のログイン試行回数制限
    "django_extensions",  # Django の管理コマンドを拡張
    # My apps
    "streamings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 3rd party middleware
    "axes.middleware.AxesMiddleware",  # 管理画面のログイン試行回数制限
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    # 3rd party backends
    "axes.backends.AxesStandaloneBackend",
]

ROOT_URLCONF = "nicodb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "nicodb.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# Docker コンテナ内で実行されているか判別
IS_RUNNING_IN_DOCKER = os.path.exists("/.dockerenv") or socket.gethostname() == "server"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "test_db"),
        "USER": os.getenv("DATABASE_USER", "test_user"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "test_password"),
        "HOST": os.getenv("DATABASE_HOST") if IS_RUNNING_IN_DOCKER else "localhost",
        "PORT": os.getenv("DATABASE_PORT"),
        "TEST": {
            "NAME": "test_db",
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "ja"

TIME_ZONE = "Asia/Tokyo"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# 静的ファイルを収集するディレクトリ
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ロギング設定
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/streaming_data.log",
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "streamings": {  # `streamings` アプリ用のロガー
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname}: {message}",
            "style": "{",
        },
    },
}

## デプロイ設定
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # HSTS を有効化し、1年間 HTTPS のみ許可
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # サブドメインにも HSTS を適用
    SECURE_HSTS_PRELOAD = True  # HSTS プリロードリストに登録（初回アクセス時から HTTPS のみで接続）
    SECURE_SSL_REDIRECT = True  # HTTP へのアクセスを HTTPS にリダイレクト
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # プロキシ経由の場合もHTTPSで通信
    SESSION_COOKIE_SECURE = True  # セッションクッキーを HTTPS でのみ送信
    CSRF_COOKIE_SECURE = True  # CSRF クッキーを HTTPS でのみ送信

# 管理画面
ADMIN_URL = os.getenv("ADMIN_URL", "admin")
AXES_FAILURE_LIMIT = int(os.getenv("AXES_FAILURE_LIMIT", 5))
AXES_COOLOFF_TIME = int(os.getenv("AXES_COOLOFF_TIME", 1))
AXES_LOCKOUT_PARAMETERS = os.getenv("AXES_LOCKOUT_PARAMETERS", "username,ip_address").split(",")
AXES_VERBOSE = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# データ取得処理
STREAMING_BASE_URL = os.getenv("STREAMING_BASE_URL")
