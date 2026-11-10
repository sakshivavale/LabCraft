"""
Django settings for LabCraft project.

Generated for LabCraft – Automated Code Execution & Practical Lab Grading Platform.
Environment variables are loaded from a .env file (never commit .env to Git).
"""

from pathlib import Path
from datetime import timedelta   # used for JWT token lifetime settings
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# BASE PATHS
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-before-going-to-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ---------------------------------------------------------------------------
# INSTALLED APPS
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'corsheaders',

    # LabCraft modules
    'accounts',
    'classrooms',
    'assignments',
    'submissions',
    'grader',
    'analytics',
]

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# DATABASE  (PostgreSQL)
# DATABASE (Uses local SQLite by default if DB_ENGINE environment variable isn't set)
# ---------------------------------------------------------------------------
DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite')

if DB_ENGINE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'labcraft_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# INTERNATIONALISATION
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# STATIC & MEDIA FILES
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# DEFAULT PRIMARY KEY
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# CUSTOM USER MODEL
# Tell Django to use OUR User model instead of the built-in one.
# IMPORTANT: This must be set before the first migration is created.
# Format: 'app_name.ModelName'
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'

# ---------------------------------------------------------------------------
# DJANGO REST FRAMEWORK
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # JWTAuthentication: reads the 'Authorization: Bearer <token>' header
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # SessionAuthentication: for the browsable API / Django Admin
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # By default, every endpoint requires a logged-in user
        # Individual views can override this (e.g. AllowAny for registration)
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ---------------------------------------------------------------------------
# SIMPLE JWT SETTINGS
# Controls how long tokens stay valid.
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    # Access token: sent with every API request — short-lived for security
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=60),   # expires in 1 hour

    # Refresh token: used to get a new access token without re-logging-in
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),       # expires in 7 days

    # When a refresh token is used, issue a new refresh token too
    'ROTATE_REFRESH_TOKENS': True,

    # Header type: clients send "Authorization: Bearer <token>"
    'AUTH_HEADER_TYPES': ('Bearer',),

    # Claims included in every token by default
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ---------------------------------------------------------------------------
# CORS (allow React frontend on port 3000)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
]

