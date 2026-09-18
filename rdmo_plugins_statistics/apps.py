from django.apps import AppConfig


class StatisticsConfig(AppConfig):
    name = 'rdmo_plugins_statistics'



    def ready(self):
        from . import rules  # noqa: F401
