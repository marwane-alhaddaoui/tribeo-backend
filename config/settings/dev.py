from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Si tu veux tester en Postgres local, décommente :
# DATABASES["default"] = {
#     "ENGINE": "django.db.backends.postgresql",
#     "NAME": "tribeo_dev",
#     "USER": "postgres",
#     "PASSWORD": "postgres",
#     "HOST": "localhost",
#     "PORT": "5432",
# }

# Stripe test en local (ou via .env)
# STRIPE_SECRET_KEY     = env("STRIPE_SECRET_KEY", default="sk_test_xxx")
# STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="whsec_xxx")
