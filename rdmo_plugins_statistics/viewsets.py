from django.contrib.sites.models import Site

from rdmo.core.permissions import HasPermission

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .serializers import (
    CatalogStatisticsSerializer,
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
