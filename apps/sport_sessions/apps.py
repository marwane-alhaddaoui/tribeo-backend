from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sport_sessions'
    label = 'sport_sessions'
    
    def ready(self):
        import apps.sport_sessions.signals