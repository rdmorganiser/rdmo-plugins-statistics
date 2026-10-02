from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _

from rdmo.questions.models import Catalog

from rest_framework import serializers


class ProjectStatisticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    created = serializers.ListField(child=serializers.DictField())
    total_over_time = serializers.ListField(child=serializers.DictField())
    progress = serializers.ListField(child=serializers.DictField())


class UserStatisticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    registered = serializers.ListField(child=serializers.DictField())
    total_over_time = serializers.ListField(child=serializers.DictField())


class CatalogStatisticsSerializer(serializers.Serializer):
    usage = serializers.ListField(child=serializers.DictField())


class ProjectsFilterSerializer(serializers.Serializer):

    class CatalogField(serializers.PrimaryKeyRelatedField):

        default_error_messages = {
            'does_not_exist': _('Select a catalog assigned to the current site.'),
        }

        def get_queryset(self):
            return Catalog.objects.filter(sites=Site.objects.get_current())

    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    catalog = CatalogField(required=False, pk_field=serializers.IntegerField(min_value=1))

    def validate(self, attrs):
        if attrs.get('start') and attrs.get('end') and attrs['start'] > attrs['end']:
            raise serializers.ValidationError(_('The start date must not be after the end date.'))
        return attrs


class ProjectDateRangeStatisticsSerializer(serializers.Serializer):
    catalog = serializers.DictField()
    project_progress = serializers.DictField()


class StatisticsSerializer(serializers.Serializer):
    projects = ProjectStatisticsSerializer()
    users = UserStatisticsSerializer()
    catalogs = CatalogStatisticsSerializer()
