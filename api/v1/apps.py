from django.apps import AppConfig


class V1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.v1'

    def ready(self):
        import api.v1.tasks    # 👈 Required to load tasks manually
        import api.v1.signals  # Import signals to activate them
