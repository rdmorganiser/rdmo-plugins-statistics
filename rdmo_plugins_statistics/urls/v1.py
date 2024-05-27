from django.urls import include, path

from rest_framework import routers

from ..viewsets import StatisticalUserViewSet, StatisticalProjectViewSet

app_name = 'v1-plugins-statistics'

router = routers.DefaultRouter()
router.register(r'user-statistics', StatisticalUserViewSet, basename='user_statistics')
router.register(r'project-statistics', StatisticalProjectViewSet, basename='project_statistics')

urlpatterns = [
    path('', include(router.urls)),
]
