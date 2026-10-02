from django.urls import include, path

from rest_framework import routers

from ..viewsets import (
    CatalogStatisticsViewSet,
    ProjectDateRangeStatisticsViewSet,
    ProjectStatisticsViewSet,
    StatisticsViewSet,
    UserStatisticsViewSet,
)

app_name = 'v1-statistics'

router = routers.DefaultRouter()
router.register(r'statistics', StatisticsViewSet, basename='statistics')
router.register(r'project-statistics', ProjectStatisticsViewSet, basename='project-statistics')
router.register(r'user-statistics', UserStatisticsViewSet, basename='user-statistics')
router.register(r'catalog-statistics', CatalogStatisticsViewSet, basename='catalog-statistics')

urlpatterns = [
    path(
        'statistics/projects/',
        ProjectDateRangeStatisticsViewSet.as_view({'get': 'list'}),
        name='project-date-range-statistics',
    ),
    path('', include(router.urls)),
]
