from django.apps import AppConfig


class EstacionamientosConfig(AppConfig):
    name = 'estacionamientos'

    def ready(self):
        from . import signals  # noqa: F401
