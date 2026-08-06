from copy import deepcopy

from django.apps import apps
from django.conf import settings as django_settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.sites.models import Site
from django.db.models import Count, Q
from django.db.models.functions import TruncDay
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from rdmo.questions.models import Catalog

from .config import DEFAULT_SETTINGS, TIME_CHART_DEFINITION
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

        current_site = Site.objects.get_current()

        settings = deepcopy(DEFAULT_SETTINGS)

        custom_settings = getattr(django_settings, 'RDMO_STATISTICS', {})

        for section, values in custom_settings.items():
            if section not in settings:
                continue

            settings[section].update({
                key: value
                for key, value in values.items()
                if key in settings[section]
            })

        time_charts = []

        for name, definition in TIME_CHART_DEFINITION.items():
            model = apps.get_model(definition['model'])

            filters = {
                lookup: current_site if value == 'current_site' else value
                for lookup, value in definition['filters'].items()
            }

            queryset = model.objects.filter(**filters)

            statistics = (
                queryset
                .annotate(period=TruncDay(definition['date_field']))
                .values('period')
                .annotate(count=Count('id'))
                .values_list('period', 'count')
                .order_by('period')
            )

            time_charts.append({
                **definition,
                **settings.get(name, {}),
                'statistics': get_time_statistics(statistics),
                'total': queryset.count(),
                'statistics_id': f"{definition['key']}-statistics-data",
                'storage_key': f"{definition['key']}-statistics-interval",
            })

        catalog_statistics = (
            Catalog.objects
            .filter(sites=current_site)
            .annotate(
                count=Count(
                    'projects',
                    filter=Q(projects__site=current_site),
                )
            )
            .order_by('id')
        )

        context.update({
            'base_template': base_template,
            'current_site': current_site,
            'statistics_settings': settings,
            'time_charts': time_charts,
            'catalog_statistics': get_catalog_statistics(catalog_statistics),
        })

        return context
