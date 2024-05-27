from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from rest_framework.viewsets import ReadOnlyModelViewSet

from rdmo.accounts.viewsets import UserViewSetMixin
from rdmo.core.permissions import HasModelPermission
from rdmo.projects.permissions import HasProjectsPermission
from rdmo.projects.models.project import Project

from .serializers.users import AnonymousUserStatisticsSerializer
from .serializers.projects import ProjectStatisticsSerializer

class StatisticalUserViewSet(UserViewSetMixin, ReadOnlyModelViewSet):
    permission_classes = (HasModelPermission | HasProjectsPermission, )
    # queryset = get_user_model().objects.all()
    serializer_class = AnonymousUserStatisticsSerializer

    filter_backends = (DjangoFilterBackend,)
    filterset_fields = (
        'role__member',
    )

    def get_queryset(self):
        return self.get_users_for_user(self.request.user) \
                   .prefetch_related('groups',
                                     'role__member', 'role__manager',
                                     'role__editor', 'role__reviewer',
                                     'memberships')

class StatisticalProjectViewSet(ReadOnlyModelViewSet):
    permission_classes = (HasModelPermission | HasProjectsPermission, )
    serializer_class = ProjectStatisticsSerializer

    filter_backends = (DjangoFilterBackend,)
    filterset_fields = (
        'site',
    )

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.has_perm('projects.view_project'):
                return Project.objects.all().select_related('catalog')
            elif user.role.manager.exists():
                return Project.objects.filter(site__in=user.role.manager.all())
            else:
                return Project.objects.filter_user(self.request.user).distinct().select_related('catalog', 'site')
        else:
            return Project.objects.none()

