from django.apps import AppConfig

class SportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sports"   # chemin paquet
    label = "sports"       # étiquette app (stable)
