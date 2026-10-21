import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Secrets come from the environment only (.env locally, GitHub/host secrets in CI and production)
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY is not set. Add it to .env (see .env.example).')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    # Apps
    'apps.accounts',
    'apps.farms',
    'apps.environmental',
    'apps.varieties',
    'apps.recommendations',
    'apps.guides',
    'apps.progress',
    'apps.predictions',
    'apps.ai',
]

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

# Database — Supabase PostgreSQL
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
    )
}

# Cache — Redis when REDIS_URL is set (Docker Compose), otherwise Django's in-memory cache
if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
        }
    }

# Print cache HIT/MISS lines to the console so caching can be shown in a demo
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'apps.environmental.services.cache': {'handlers': ['console'], 'level': 'INFO'},
        # riceflow.security: failed logins, 403s, 429s; riceflow.errors: unhandled exceptions
        'riceflow': {'handlers': ['console'], 'level': 'INFO'},
    },
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Argon2 for new passwords. The others stay so existing PBKDF2 hashes still verify;
# Django re-hashes them with Argon2 the next time each user logs in.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Django serves its own static files (admin CSS/JS) via WhiteNoise after collectstatic
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    # Rate limits (HTTP 429 with a Retry-After header). Counts live in the cache (Redis in Docker).
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',  # only views that set throttle_scope
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '300/hour',
        'user': '3000/hour',
        'login': '10/min',      # per IP: slows password guessing
        'register': '10/hour',  # per IP: stops mass sign-ups
        'ai_chat': '60/hour',   # per user: caps Gemini usage
    },
    # Proxies in front of Django (nginx, Render, ngrok) so throttles use the real client IP
    # from X-Forwarded-For instead of a value the client could fake
    'NUM_PROXIES': int(os.getenv('NUM_PROXIES', '1')),
    # Logs 403s/429s and turns unexpected errors into a JSON 500 without a stack trace
    'EXCEPTION_HANDLER': 'config.exceptions.exception_handler',
}

# JWT
SIMPLE_JWT = {
    # Short access tokens limit the damage of a leaked token; the apps refresh them on a 401
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    # A refresh token works once: refreshing or logging out puts it on the blacklist
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS — allow mobile app
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8081',
    'http://localhost:19006',
    'http://127.0.0.1:8081',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://192.168.1.100:5173',  # Replace with your actual IP address
]

# Panabo City constants
PANABO_LAT = float(os.getenv('PANABO_LAT', 7.3086))
PANABO_LON = float(os.getenv('PANABO_LON', 125.6830))

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')

# Trained model storage path
MODELS_DIR = BASE_DIR / 'models' / 'trained'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Production security (the host terminates HTTPS and forwards X-Forwarded-Proto)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
    SECURE_REDIRECT_EXEMPT = [r'^api/health/$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
