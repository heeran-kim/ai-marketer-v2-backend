"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 5.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from pathlib import Path
from datetime import timedelta
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if not os.getenv("DOCKER_RUNNING"):
    from dotenv import load_dotenv
    load_dotenv()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# Django Security Settings
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set.")

TWOFA_ENCRYPTION_KEY = os.getenv("TWOFA_ENCRYPTION_KEY")
if not TWOFA_ENCRYPTION_KEY:
    raise ValueError("TWOFA_ENCRYPTION_KEY environment variable is not set.")

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
if not FACEBOOK_APP_ID:
    raise ValueError("FACEBOOK_APP_ID environment variable is not set. Read Dan's documentation or just put random letters for now to bypass this error!")

FACEBOOK_SECRET = os.getenv("FACEBOOK_SECRET")
if not FACEBOOK_SECRET:
    raise ValueError("FACEBOOK_SECRET environment variable is not set. Read Dan's documentation or just put random letters for now to bypass this error!")

FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")
if not FACEBOOK_REDIRECT_URI:
    raise ValueError("FACEBOOK_REDIRECT_URI environment variable is not set. Read Dan's documentation or just put random letters for now to bypass this error!")


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = [
    host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host
]


# Application definition
INSTALLED_APPS = [
    "drf_spectacular",
    "rest_framework",
    'rest_framework_simplejwt', # JWT Authentication
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'users',
    'businesses',
    'social',
    'posts',
    'promotions',
    'ai',
    'sales',
    "django_extensions",
]

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1), # Access Token expiration time
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7), # Refresh Token expiration time
    "ROTATE_REFRESH_TOKENS": True, # Issue a new Refresh Token when issuing a new Access Token
    "BLACKLIST_AFTER_ROTATION": True, # Invalidate the previous Refresh Token after rotation
    "AUTH_HEADER_TYPES": ("Bearer",),

    # HttpOnly Cookie
    "AUTH_COOKIE": "access_token", # Cookie name for storing the Access Token
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SECURE": True,
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_SAMESITE": "None",
}

SESSION_COOKIE_SECURE = SIMPLE_JWT["AUTH_COOKIE_SECURE"]

# CSRF Settings
CSRF_COOKIE_SECURE = SIMPLE_JWT["AUTH_COOKIE_SECURE"]
CSRF_COOKIE_DOMAIN = None 
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "https://localhost:3000,https://127.0.0.1:3000").split(",")

# CORS Settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "https://localhost:3000,https://127.0.0.1:3000,https://ai-marketer-v2-frontend.vercel.app"
).split(",")

# DRF Default Authentication Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        "users.authentication.CustomJWTAuthentication", # http cookie
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'AI Marketer V2 API',
    'DESCRIPTION': 'API documentation for AI Marketer V2, an AI-powered marketing automation platform for restaurants and small businesses.',
    'VERSION': '1.0.0',

    # Explicitly define tag order and descriptions
    'TAGS': [
        {
            'name': 'users',
            'description': 'User authentication and account management endpoints. Includes traditional register, login, and logout functionality with JWT tokens stored in HTTP-only cookies. Current implementation supports email-based authentication. Planned future enhancements include forgot password, social media logins (Google, Facebook, Apple), passkey support (Face ID/fingerprint), and 2FA.'
        },
        {
            'name': 'businesses',
            'description': 'Business profile management for restaurant configuration. Enables business owners to set up and customize their business profile including name, logo, business category, target customers, and business branding/vibe. The current implementation supports basic business information management. Future enhancements will include social media integration and bulk sales data uploads.'
        },
        {
            'name': 'dashboard',
            'description': 'Business dashboard data and metrics. Provides an overview of key business metrics including post statistics, linked social platforms, and recent activity. Current implementation shows basic business metrics and post summary.'
        },
        {
            'name': 'posts',
            'description': 'Social media post management system. Allows creating, scheduling, and monitoring posts across multiple platforms. Current implementation supports storing and displaying posts in the database and scheduling functionality. Future features will add social media API integration for live post fetching, automatic publishing of scheduled posts, editing capabilities, comment interaction, and Discord webhook notifications.'
        },
        {
            'name': 'promotions',
            'description': 'Marketing promotion management. Enables businesses to create, track, and analyze promotional campaigns. Current implementation includes viewing promotions and creating posts from promotions. Future enhancements will add AI-driven promotion suggestions based on sales data and social media trends.'
        },
        {
            'name': 'social',
            'description': 'Social media platform integration endpoints. Provides functionality to connect, manage, and interact with various social media platforms. Includes linking social accounts to businesses, fetching platform-specific data, and enabling cross-platform publishing capabilities. Current implementation supports platform connection setup. Future enhancements will include direct comment management, social activity notifications, engagement analytics, and Discord webhook integration for real-time alerts.'
        },
        {
            'name': 'ai',
            'description': 'AI-powered content creation tools. Provides machine learning capabilities for analyzing images, generating captions, and suggesting hashtags. Frontend implementation of image analysis and caption generation is complete, but backend AI integration is under development. Uses ChatGPT API for natural language processing and will support multi-platform content publishing.'
        }
    ],
}

# Middleware Settings
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", # Add CORS middleware near the top
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Django Admin & Template Setting
ROOT_URLCONF = "backend.urls"
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
WSGI_APPLICATION = "backend.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASES = {
    "default": dj_database_url.config(default=os.getenv("DATABASE_URL"))
    if os.getenv("USE_RENDER_DB") == "true"
    else {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
#     },
#     {
#         "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
#     },
#     {
#         "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
#     },
#     {
#         "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
#     },
# ]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

# LANGUAGE_CODE = "en-us"
#
TIME_ZONE = 'UTC'
#
# USE_I18N = True
#
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django Auth Setting
AUTH_USER_MODEL = 'users.User'
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "users": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}