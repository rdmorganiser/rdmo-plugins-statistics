from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.sites.models import Site
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from .charts import compute_dashboard_charts
from .statistics import fetch_statistics


class StatisticsView(PermissionRequiredMixin, TemplateView):
    template_name = 'rdmo_plugins_statistics/statistics.html'
    permission_required = 'statistics.view_statistics'
    raise_exception = True

    @staticmethod
    def get_base_template():
        try:
            get_template('core/bs53/base.html')
            return 'core/bs53/base.html'
        except TemplateDoesNotExist:
            return 'core/base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_site = Site.objects.get_current()
        context.update({
            'base_template': self.get_base_template(),
            'current_site': current_site,
            **compute_dashboard_charts(fetch_statistics(current_site)),
        })

        return context
