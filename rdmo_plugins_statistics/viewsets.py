from django.contrib.sites.models import Site

from rdmo.core.permissions import HasPermission

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .charts import compute_catalog_statistics, compute_project_progress_statistics
from .config import CATEGORY_CHART_DEFINITION
from .serializers import (
    CatalogStatisticsSerializer,
    ProjectDateRangeSerializer,
    ProjectDateRangeStatisticsSerializer,
    ProjectStatisticsSerializer,
    StatisticsSerializer,
    UserStatisticsSerializer,
)
from .statistics import (
    fetch_catalog_statistics,
    fetch_project_statistics,
    fetch_statistics,
    fetch_user_statistics,
)


class StatisticsViewSet(GenericViewSet):
    permission_classes = (HasPermission,)
    permission_required = 'statistics.view_statistics'
    serializer_class = StatisticsSerializer

    def list(self, request, *args, **kwargs):
        statistics = fetch_statistics(Site.objects.get_current())
        return Response(self.get_serializer(statistics).data)


class ProjectStatisticsViewSet(GenericViewSet):
    permission_classes = (HasPermission,)
    permission_required = 'statistics.view_statistics'
    serializer_class = ProjectStatisticsSerializer

    def list(self, request, *args, **kwargs):
        statistics = fetch_project_statistics(Site.objects.get_current())
        return Response(self.get_serializer(statistics).data)


class UserStatisticsViewSet(GenericViewSet):
    permission_classes = (HasPermission,)
    permission_required = 'statistics.view_statistics'
    serializer_class = UserStatisticsSerializer

    def list(self, request, *args, **kwargs):
        statistics = fetch_user_statistics(Site.objects.get_current())
        return Response(self.get_serializer(statistics).data)


class CatalogStatisticsViewSet(GenericViewSet):
    permission_classes = (HasPermission,)
    permission_required = 'statistics.view_statistics'
    serializer_class = CatalogStatisticsSerializer

    def list(self, request, *args, **kwargs):
        statistics = fetch_catalog_statistics(Site.objects.get_current())
        return Response(self.get_serializer(statistics).data)


class ProjectDateRangeStatisticsViewSet(GenericViewSet):
    permission_classes = (HasPermission,)
    permission_required = 'statistics.view_statistics'
    serializer_class = ProjectDateRangeStatisticsSerializer

    def list(self, request, *args, **kwargs):
        query = {
            serializer_name: request.query_params[parameter_name]
            for parameter_name, serializer_name in (('from', 'start'), ('to', 'end'))
            if parameter_name in request.query_params
        }
        filters = ProjectDateRangeSerializer(data=query)
        filters.is_valid(raise_exception=True)
        start, end = filters.validated_data.get('start'), filters.validated_data.get('end')

        site = Site.objects.get_current()
        projects = fetch_project_statistics(site, start=start, end=end)
        catalogs = fetch_catalog_statistics(site, start=start, end=end)
        statistics = {
            'catalog': compute_catalog_statistics(catalogs['usage']),
            'project_progress': compute_project_progress_statistics(
                projects['progress'],
                CATEGORY_CHART_DEFINITION['project_progress']['progress_group_size'],
            ),
        }
        return Response(self.get_serializer(statistics).data)
