import os
import sys
import warnings
from pathlib import Path
from decouple import config
import dj_database_url  # <-- ajoute ce paquet dans requirements.txt

def env(key: str, default=None, required: bool = False):
    val = os.getenv(key)
    if not val:
        try:
            from decouple import config as _config
            val = _config(key, default=None)
        except Exception:
            val = None
    if (val is None or val == "") and required and default is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val if val not in (None, "") else default

# ATTENTION: base.py est désormais dans config/settings/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# --- FLAGS & HOSTS ---
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key')
DEBUG = config('DEBUG', default=False, cast=bool)

def _split_csv(val, default=""):
    raw = val if isinstance(val, str) else default
    return [x.strip() for x in raw.split(",") if x.strip()]

ALLOWED_HOSTS = _split_csv(config("ALLOWED_HOSTS", default="127.0.0.1,localhost"))
CORS_ALLOWED_ORIGINS = _split_csv(config("CORS_ALLOWED_ORIGINS", default=""))
CSRF_TRUSTED_ORIGINS = _split_csv(config("CSRF_TRUSTED_ORIGINS", default="http://127.0.0.1:8000,http://localhost:8000"))

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'apps.audit',
    'apps.users',
    'apps.sport_sessions',
    'apps.sports',
    'apps.groups',
    'apps.teams',
    'apps.chat',
    'apps.billing',
    "drf_spectacular",
    "drf_spectacular_sidecar",
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- DATABASE ---
DATABASE_URL = config("DATABASE_URL", default=None)
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,  # Render Postgres → SSL obligatoire
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
DEFAULT_AVATAR_URL = STATIC_URL + "img/logo.png"
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    
    #  Anti brute force / spam
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',     
        'user': '600/min',    
        'login': '3/min',     
        'register': '10/hour' 
    },
}

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Tribeo API',
    'DESCRIPTION': 'API REST pour TRIBEO.',
    'VERSION': '1.0.0',
    'SCHEMA_PATH_PREFIX': r'/api/',  # documenter uniquement /api/
    'COMPONENT_SPLIT_REQUEST': True,
    'SECURITY': [{'BearerAuth': []}],
    'COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
}
AUTH_USER_MODEL = 'users.CustomUser'

GROUP_CREATION_POLICY = "ANY_MEMBER"  # "COACH_ONLY" | "PREMIUM_ONLY" | "COACH_OR_PREMIUM"

PLAN_LIMITS = {
    "FREE": {
        "sessions_create_per_month": 1,
        "sessions_join_per_month": 3,
        "max_groups": 1,
        "can_create_groups": False,
        "trainings_create_per_month": 0,
        "can_create_trainings": False,
    },
    "PREMIUM": {
        "sessions_create_per_month": None,
        "sessions_join_per_month": None,
        "max_groups": None,
        "can_create_groups": True,
        "trainings_create_per_month": 0,
        "can_create_trainings": False,
    },
    "COACH": {
        "sessions_create_per_month": 20,
        "sessions_join_per_month": None,
        "max_groups": None,
        "can_create_groups": True,
        "trainings_create_per_month": None,
        "can_create_trainings": True,
    },
}

STRIPE_SECRET_KEY     = env("STRIPE_SECRET_KEY", required=True)
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_PRODUCTS = {
    "premium_month": {"price_id": env("STRIPE_PRICE_PREMIUM_MONTH", required=True)},
    "coach_month":   {"price_id": env("STRIPE_PRICE_COACH_MONTH", default="")},
}
STRIPE_ENABLE_VERIFY = os.getenv("STRIPE_ENABLE_VERIFY", "false").lower() == "true"
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

for _plan, _cfg in STRIPE_PRODUCTS.items():
    if not _cfg.get("price_id"):
        warnings.warn(f"[Billing] STRIPE_PRODUCTS[{_plan}].price_id is empty — this plan cannot be purchased.")
