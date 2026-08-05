from django.apps import apps
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


def get_time_statistics(queryset, date_field):
    statistics = (
        queryset
        .annotate(period=TruncDay(date_field))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )

    return {
        'day': {
            'rows': [
                {
                    'key': item['period'].isoformat(),
                    'label': item['period'].isoformat(),
                    'value': item['count'],
                }
                for item in statistics
            ],
        },
    }


def get_catalog_statistics(current_site):
    statistics = (
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

    return {
        'rows': [
            {
                'key': catalog.id,
                'label': catalog.title,
                'value': catalog.count,
                **({'label_suffix': ' *'} if not catalog.available else {}),
            }
            for catalog in statistics
        ],
    }

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

        context.update({
            'base_template': base_template,
            'current_site': current_site,
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
