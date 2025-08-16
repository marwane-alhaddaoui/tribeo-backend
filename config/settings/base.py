import os
import sys
import warnings
from pathlib import Path
from decouple import config

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

# Neutralise en "base" → override dans dev/prod
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key')  # en prod: var d'env
DEBUG = False
ALLOWED_HOSTS = []

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
     'apps.users',
     'apps.sport_sessions',
     'apps.sports',
     'apps.groups',
     'apps.teams',
     'apps.chat',
     'apps.billing',
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
DEFAULT_AVATAR_URL = STATIC_URL + "img/logo.png" 
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = []
CSRF_TRUSTED_ORIGINS = []

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
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
    "sessions_create_per_month": None,  # ∞
    "sessions_join_per_month":   None,  # ∞
    "max_groups":                None,  # ∞
    "can_create_groups": True,
    "trainings_create_per_month": 0,
    "can_create_trainings": False,
  },
  "COACH": {
    "sessions_create_per_month": 20,  # sessions classiques ∞
    "sessions_join_per_month":   None,
    "max_groups":                None,
    "can_create_groups": True,
    "trainings_create_per_month": None,   # <— limite coach (ex.)
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
        

