from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StatisticsConfig(AppConfig):
    name = 'rdmo_plugins_statistics'

    navigation_items = (
        {
            'name': 'statistics',
            'label': _('Statistics'),
            'url_name': 'statistics:index',
            'order': 100,
            'permission': 'statistics.view_statistics',
        },
    )

    def ready(self):
      from . import rules  # noqa: F401
