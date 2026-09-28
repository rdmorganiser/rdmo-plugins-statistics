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


class ProjectDateRangeSerializer(serializers.Serializer):
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get('start') and attrs.get('end') and attrs['start'] > attrs['end']:
            raise serializers.ValidationError('The start date must not be after the end date.')
        return attrs


class ProjectDateRangeStatisticsSerializer(serializers.Serializer):
    catalog = serializers.DictField()
    project_progress = serializers.DictField()


class StatisticsSerializer(serializers.Serializer):
    projects = ProjectStatisticsSerializer()
    users = UserStatisticsSerializer()
    catalogs = CatalogStatisticsSerializer()
