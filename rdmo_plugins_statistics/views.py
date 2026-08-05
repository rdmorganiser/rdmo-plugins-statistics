from copy import deepcopy

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.sites.models import Site
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from rdmo.projects.models import Project

from .config import DEFAULT_STATISTICS_CONFIG
from .utils import get_catalog_statistics, get_time_statistics


class StatisticsView(PermissionRequiredMixin, TemplateView):
    template_name = 'rdmo_plugins_statistics/statistics.html'
    permission_required = (
        apps.get_app_config('rdmo_plugins_statistics')
        .navigation_items[0]
        .get('permission')
    )
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            get_template('core/bs53/base.html')
            base_template = 'core/bs53/base.html'
        except TemplateDoesNotExist:
            base_template = 'core/base.html'

        User = get_user_model()
        current_site = Site.objects.get_current()

        config = deepcopy(DEFAULT_STATISTICS_CONFIG)

        custom_config = getattr(settings, 'RDMO_STATISTICS', {})

        for section, values in custom_config.items():
            config[section].update(values)

        context.update({
            'base_template': base_template,
            'current_site': current_site,
            'statistics_config': config,
            'project_statistics': get_time_statistics(
                Project.objects.filter(site=current_site),
                'created',
            ),
            'user_statistics': get_time_statistics(
                User.objects.filter(role__member=current_site),
                'date_joined',
            ),
            'catalog_statistics': get_catalog_statistics(current_site),
        })

        return context
