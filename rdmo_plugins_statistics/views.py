from django.apps import apps
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.sites.models import Site
from django.db.models import Count, Q
from django.db.models.functions import TruncDay
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from rdmo.projects.models import Project
from rdmo.questions.models import Catalog

from .config import (
    CATEGORY_CHART_DEFINITION,
    CATEGORY_CHART_SETTINGS,
    TIME_CHART_DEFINITION,
    TIME_CHART_SETTINGS,
)
from .utils import get_category_statistics, get_time_statistics


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

        User = get_user_model()

        time_chart_querysets = {
            'project': Project.objects.filter(site=current_site),
            'user': User.objects.filter(role__member=current_site),
        }
        custom_settings = getattr(django_settings, 'RDMO_STATISTICS', {})

        time_charts = []

        for name, definition in TIME_CHART_DEFINITION.items():
            queryset = time_chart_querysets[definition['query_key']]

            statistics = (
                queryset
                .annotate(period=TruncDay(definition['date_field']))
                .values('period')
                .annotate(count=Count('id'))
                .values_list('period', 'count')
                .order_by('period')
            )

            calculation = definition['calculation']

            if calculation not in {'period_count', 'cumulative_count'}:
                raise ValueError(
                    f'Unsupported time chart calculation: {calculation}'
                )

            statistics_data = get_time_statistics(
                statistics,
                calculation,
            )

            time_charts.append({
                **definition,
                **{
                    key: value
                    for key, value in custom_settings.get(name, {}).items()
                    if key in TIME_CHART_SETTINGS
                },
                'statistics': statistics_data,
                'total': queryset.count(),
            })

        category_chart_querysets = {
            'catalog': [
                {
                    'key': catalog.id,
                    'label': catalog.title,
                    'value': catalog.count,
                    'label_suffix': ' *' if not catalog.available else '',
                }
                for catalog in (
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
            ],
            'project-progress': [
                {
                    'key': project.id,
                    'label': project.title,
                    'value': round(
                        100 * project.progress_count /
                        project.progress_total
                    ) if (
                        project.progress_count is not None and
                        project.progress_total
                    ) else 0,
                }
                for project in (
                    Project.objects
                    .filter(site=current_site)
                    .order_by('id')
                )
            ],
        }

        category_charts = []

        for name, definition in CATEGORY_CHART_DEFINITION.items():
            queryset = category_chart_querysets[definition['query_key']]

            statistics_data = get_category_statistics(queryset)

            chart_settings = {
                key: value
                for key, value in custom_settings.get(name, {}).items()
                if key in CATEGORY_CHART_SETTINGS
            }

            chart = {
                **definition,
                **chart_settings,
                'statistics': statistics_data,
            }

            opposite_orientation = {
                'horizontal': 'vertical',
                'vertical': 'horizontal',
            }[definition['orientation']]

            if chart_settings.get('orientation') == opposite_orientation:
                chart['x_axis_title'], chart['y_axis_title'] = (
                    chart['y_axis_title'],
                    chart['x_axis_title'],
                )

            category_charts.append(chart)

        context.update({
            'base_template': base_template,
            'current_site': current_site,
            'time_charts': time_charts,
            'category_charts': category_charts,
        })

        return context
